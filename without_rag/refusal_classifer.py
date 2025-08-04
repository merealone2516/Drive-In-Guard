from without_rag.manual_classification_helper import prompt_manual_classification_gui

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import json
import csv

tokenizer = AutoTokenizer.from_pretrained("ProtectAI/distilroberta-base-rejection-v1")
model = AutoModelForSequenceClassification.from_pretrained(
    "ProtectAI/distilroberta-base-rejection-v1"
)

classifier = pipeline(
    "text-classification",
    model=model,
    tokenizer=tokenizer,
    truncation=True,
    max_length=512,
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
)


table = []
with open("prompts.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    table = [row for row in reader]

MODELS = ["DeepSeek", "LLaMA", "Claude", "ChatGPT", "Mistral", "Gemma"]

with open("output.csv", encoding="utf-8", mode="w", newline="") as f:
    keys = list(table[0].keys()) + [f"{m}_Auto_Clean" for m in MODELS]
    writer = csv.DictWriter(f, keys)
    writer.writeheader()
    for i, row in enumerate(table):
        print(f"Classifying row {i}")
        for model in MODELS:
            classification = classifier(row[model])
            print(classification)
            row[f"{model}_Auto_Clean"] = str(classification[0]["label"])
            if str(classification[0]["label"]) == "REJECTION":
                prompt_manual_classification_gui(row, model)
            else:
                row[f"{model}_Manual_Clean"] == "NORMAL"
        writer.writerow(row)

with open("prompts_with_mutations.json", encoding="utf-8") as f:
    prompts = json.load(f)

    for i, prompt in enumerate(prompts):
        print(f"Starting prompt {i}")
        for model in ["DeepSeek", "LLaMA", "Claude", "ChatGPT", "Mistral", "Gemma"]:
            mutations_auto_class = []
            for output in prompt[f"{model}_Mutations_Output"]:
                mutations_auto_class.append(classifier(output)[0]["label"])
            prompt[f"{model}_Mutations_Output_Auto_Clean"] = mutations_auto_class

    with open("mutations_output.json", "w") as g:
        json.dump(prompts, g)
