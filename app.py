# HackproofHacks AI Security Lab | @trickyhash | github.com/th3hash
import ast
import operator
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

PDF_PATH = "handbook.pdf"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "rag_agent_target"
OLLAMA_MODEL = "llama3.2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# -----------------------------
# Safe local calculator
# -----------------------------

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_math(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_math(node.operand))

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left = _eval_math(node.left)
        right = _eval_math(node.right)

        # Keep this demo calculator bounded.
        if abs(left) > 10**12 or abs(right) > 10**12:
            raise ValueError("Number is outside the calculator limit.")

        return _ALLOWED_OPERATORS[type(node.op)](left, right)

    raise ValueError("Only basic arithmetic is supported.")


def calculator(expression: str) -> str:
    """Calculate a basic arithmetic expression."""
    tree = ast.parse(expression, mode="eval")
    result = _eval_math(tree.body)

    if isinstance(result, float) and result.is_integer():
        result = int(result)

    return str(result)


# -----------------------------
# RAG tool
# -----------------------------

def build_vectorstore():
    if not Path(PDF_PATH).exists():
        raise FileNotFoundError(
            f"Could not find {PDF_PATH}. Put your PDF in the project root."
        )

    docs = PyPDFLoader(PDF_PATH).load()
    print(f"Loaded {len(docs)} pages.")

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    ).split_documents(docs)

    print(f"Created {len(chunks)} chunks.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
    )

    return vectorstore


def make_search_documents_tool(vectorstore):
    def search_documents(question: str) -> str:
        """Search the authorized PDF and return relevant document passages."""
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": TOP_K}
        )
        docs = retriever.invoke(question)

        if not docs:
            return "No relevant document passages were found."

        results = []
        for index, doc in enumerate(docs, start=1):
            page = doc.metadata.get("page", "?")
            results.append(
                f"[Chunk {index} | page {page}]\n{doc.page_content}"
            )

        return "\n\n".join(results)

    return search_documents


# -----------------------------
# Agent
# -----------------------------

def main():
    vectorstore = build_vectorstore()

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0,
    )

    search_documents = make_search_documents_tool(vectorstore)

    tools = [
        search_documents,
        calculator,
    ]

    system_prompt = """You are a local educational AI agent.

You have two tools:
1. search_documents — use it for facts that may be contained in the PDF.
2. calculator — use it for arithmetic.

Use tools when they are appropriate.
For a question requiring both document information and arithmetic,
use search_documents first, then calculator.

Do not invent information that was not returned by search_documents.
Do not claim that a tool was used when it was not used.
"""

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    print("\nRAG + Agent ready.")
    print("Tools: search_documents, calculator")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not question:
            continue

        print("\n--- AGENT TRACE ---")

        try:
            final_answer = None

            for update in agent.stream(
                {"messages": [{"role": "user", "content": question}]},
                stream_mode="updates",
            ):
                print(update)

                # The final assistant message is available in the updates.
                messages = update.get("model", {}).get("messages", [])
                for message in messages:
                    if getattr(message, "content", None):
                        final_answer = message.content

            print("\n--- FINAL ANSWER ---")
            print(final_answer or "No final answer returned.")

        except Exception as exc:
            print(f"\nAgent error: {exc}")


if __name__ == "__main__":
    main()
