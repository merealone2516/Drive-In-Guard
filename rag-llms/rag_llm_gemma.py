import csv
from datetime import datetime
from enum import Enum, auto
import json
from typing import Callable
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.document_loaders.json_loader import JSONLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict

# Include here the prompts from the dataset that the LLM should accept, so they 
# shouldn't be included in the vector store for the RAG LLM or the testing data
PROMPTS_TO_IGNORE: set[str] = set()

mutations_to_prompts = {}
with open("prompts_with_mutations.json") as f:
    prompts = json.load(f)
    for prompt in prompts:
        for mut in prompt["Mutations"]:
            mutations_to_prompts[mut] = prompt["Prompts"]

llm = ChatOllama(
    model="gemma3",
    temperature=0.5,
)

embeddings = OllamaEmbeddings(model="nomic-embed-text")

vector_store = None


def metadata_func(record: dict, metadata: dict) -> dict:
    metadata["scenario description"] = record.get("Scenario Description")
    metadata["prompt"] = record.get("Prompts")
    metadata["benchmark_file_line"] = record.get("benchmark_file_line")

    return metadata


loader = JSONLoader(file_path="./prompts_with_mutations.json", jq_schema=".[].Mutations[]")

documents = [
    document
    for document in loader.load()
    if mutations_to_prompts[document.page_content] not in PROMPTS_TO_IGNORE
]
print(
    f"Loaded {len(documents)} mutated prompts (ignoring {len(PROMPTS_TO_IGNORE)} base prompts)"
)

system_prompt = ""
with open("prompt.md") as f:
    system_prompt = f.read()


prompt_template = ChatPromptTemplate(
    [
        ("system", system_prompt),
        ("user", "RETRIEVED CONTEXT: {context}\nUSER QUERY: {question}"),
    ]
)


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


# Define application steps
def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}


def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt_template.invoke(
        {"question": state["question"], "context": docs_content}
    )
    response = llm.invoke(messages)
    return {"answer": response.content}


# Compile application and test
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()


def llm_output_to_accept_reject(output: str) -> str:
    if "REJECT" in output.upper():
        return "REJECT"
    elif "LET THROUGH" in output.upper():
        return "ACCEPT"
    else:
        result = None
        while result != "LT" and result != "R":
            result = input(
                f"Got something other than LET THROUGH or REJECT: {output}\nPlease manually classify it by typing either LT (for LET THROUGH) or R (for REJECT): "
            )
        return "ACCEPT" if result == "LT" else "REJECT"


class CrossValidationType(Enum):
    SimpleFifths = auto()
    JackknifedBasePrompts = auto()
    EveryFifth = auto()
    Disabled = auto()


def run_with_cross_validation(
    filename: str,
    out_file: str,
    to_prompt_text: Callable[[any], str],
    cross_validation_type: CrossValidationType = CrossValidationType.SimpleFifths,
):
    """
    Do the classification with optional cross validation. We train (i.e. include in
    vector store) on only mutated prompts and test on only their corresponding base
    prompts in all cases.

    filename: path to the file with the data -- must end with .csv or .json
    out_file: path to file to output results per prompt
    to_prompt_text: function that recieves a prompt object from the file and returns
        just the text to prompt the model with
    cross_validation_type: defaults to SimpleFifths, for other options see
        CrossValidationType enum
    """
    global vector_store
    N = len(documents)
    responses = {"ACCEPT": 0, "REJECT": 0}

    get_reader = None
    if filename.endswith(".csv"):
        get_reader = lambda f: list(csv.DictReader(f))
    elif filename.endswith(".json"):
        get_reader = lambda f: json.load(f)
    else:
        raise ValueError("File type not supported")

    # default values for disabled
    OUTER_RANGE = 1
    CONDITION_FOR_TESTING = lambda i, j: False
    DISABLED_FLAG = True
    if cross_validation_type == CrossValidationType.SimpleFifths:
        OUTER_RANGE = 5
        CONDITION_FOR_TESTING = lambda i, j: (j // (N / 5)) == i
        DISABLED_FLAG = False
    elif cross_validation_type == CrossValidationType.EveryFifth:
        OUTER_RANGE = 5
        CONDITION_FOR_TESTING = lambda i, j: (j % 5) == i
        DISABLED_FLAG = False
    elif cross_validation_type == CrossValidationType.JackknifedBasePrompts:
        OUTER_RANGE = N // 5
        CONDITION_FOR_TESTING = lambda i, j: (j // (N / OUTER_RANGE)) == i
        DISABLED_FLAG = False

    to_output = []
    for i in range(OUTER_RANGE):
        print(
            f"Generating embeddings for cross fold {i+1}/{OUTER_RANGE} at {datetime.now().time()}..."
        )
        vector_store = InMemoryVectorStore(embeddings)
        training = []
        for j, document in enumerate(documents):
            if CONDITION_FOR_TESTING(i, j):
                pass
            else:
                training.append(document)
        vector_store.add_documents(documents=training)

        print(
            f"Doing retrieval for cross fold {i+1}/{OUTER_RANGE} at {datetime.now().time()}..."
        )
        with open(filename) as f:
            reader = get_reader(f)
            N = len(reader)
            for j, prompt in enumerate(reader):
                if not (
                    (type(prompt) == str and prompt in PROMPTS_TO_IGNORE)
                    or (type(prompt) != str and prompt["Prompts"] in PROMPTS_TO_IGNORE)
                ) and (CONDITION_FOR_TESTING(i, j) or DISABLED_FLAG):
                    raw_output = graph.invoke({"question": to_prompt_text(prompt)})[
                        "answer"
                    ]
                    output = llm_output_to_accept_reject(raw_output)
                    if type(prompt) != str:
                        prompt["Classification"] = output
                        to_output.append(prompt)
                    else:
                        to_output.append((prompt, output))
                    responses[output] += 1

    with open(out_file, "w") as g:
        json.dump(to_output, g)
    return responses


benchmark = run_with_cross_validation(
    "benchmark.csv",
    "benchmark run with simple fifths.json",
    lambda p: p["Prompts"],
    CrossValidationType.SimpleFifths,
)
print(
    f"benchmark run with simple fifths cross validation (want all rejected): {benchmark}"
)

accepted = run_with_cross_validation(
    "queries_that_should_be_accepted.json",
    "should_be_accepted_results.json",
    lambda p: p,
    CrossValidationType.Disabled,
)
print(f"accepted run (want all accepted): {accepted}")