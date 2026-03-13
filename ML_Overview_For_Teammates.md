# Project Overview: ML Risk Register Extractor

Welcome to the project! This document gives a high-level overview of what our code does, how it works, and what the different pieces mean in plain English. If you don't have a background in artificial intelligence (AI) or machine learning (ML), you're in the right place!

## 🎯 What are we building?
We are building a tool that reads messy, unstructured "Risk Registers" (documents that list potential project risks) in Excel or PDF formats, and automatically converts them into a clean, standardized, and machine-readable tabular format (JSON/Excel).

To do this, we use an AI model called **Claude 3.5 Sonnet**, created by Anthropic. Claude acts like a super-smart assistant that reads the document and pulls out the risks.

## 🧠 How does the AI "learn"?
We use a technique called **"Few-Shot Learning"**.
Normally, to train an AI, you need thousands of examples, powerful computers, and weeks of training. But modern LLMs (Large Language Models) like Claude are already so smart that you can just give them instructions and a **few examples** (a "few shots"), and they'll figure out the pattern immediately.

So, instead of "training" a model from scratch, our code simply takes a few pairs of `[Input Document] + [Correct Output]` and feeds them to Claude along with the new document. Claude uses those examples as a blueprint for the output we want.

## 📂 The important files explained:

- **`few_shot.json`**
  This file contains our "examples." It holds the text from old Risk Registers and their perfectly formatted JSON versions. We feed this to Claude so it knows what to do.

- **`prepare_few_shot.py`**
  This script manually bundles up our training examples into the `few_shot.json` file mentioned above. It's a preparation step.

- **`build_model.py`**
  This script is cool: it writes another script. It takes our examples from `few_shot.json` and embeds them directly into a fresh, standalone Python file named `model.py`. It's a "code generator" of sorts.

- **`model.py`** (The Final Tool)
  This is the final script that actually does the work. It takes the target input directory, extracts text from files (using `pdfplumber` for PDFs or `pandas` for Excel), sends that text + the few-shot examples to Claude, and saves Claude's formatted answers into the output directory.

- **`evaluate.py`** & **`score.py`**
  These are grading tools. After the AI creates the output, these scripts open the created files and compare them cell-by-cell and column-by-column against the known fully-correct "target" files to see how accurate our AI was.

- **`check_schema.py`** & **`check_input_schema.py`**
  Validation tools. They quickly check whether our data fits the strict column rules needed for the competition.

## 🚀 How the main pipeline (`model.py`) flows:
1. **Load:** Reads the `.pdf` or `.xlsx` file.
2. **Extract:** Converts the messy file into raw text.
3. **Prompt:** Wraps the text with our instructions ("You are an expert Data Engineer... here are 3 examples... now extract this new text.").
4. **Call AI:** Sends the prompt over the internet to Anthropic's Claude API.
5. **Parse:** Receives Claude's text response, cleans it up, and converts it back into JSON logic.
6. **Save:** Saves the final JSON structure into an Excel table.

That's it! If you ever get lost, just read the inline comments attached to the python files (`# like this`). They are written explicitly for you!
