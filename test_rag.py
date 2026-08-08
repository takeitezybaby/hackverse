import os
from rag import CampusRAG

# Ensure local Ollama host is reachable
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

def run_test():
    print("🚀 Initializing CampusRAG...")
    rag = CampusRAG()

    # 1. Seed historical documents
    print("📦 Seeding context into FAISS...")
    historical_notes = [
        "Main Library occupancy spikes to 95% between 14:00 and 17:00 on weekdays.",
        "North Cafeteria queue time drops under 5 minutes after 13:45.",
        "Campus Gym area B (free weights) remains moderate (<60%) during morning hours."
    ]
    rag.add_documents(historical_notes)
    print(f"Indexed {rag.index.ntotal} document(s) in FAISS.")

    # 2. Test Mode 1: General Query
    print("\n--- Testing Mode 1: General Query ---")
    live_state = "Main Library: 92% (Overflow), North Cafeteria: 40% (Moderate)"
    query = "Is it a good time to study at the main library right now?"
    response_mode_1 = rag.answer_general_query(query, live_state)
    print(f"User Query: {query}")
    print(f"Copilot Output:\n{response_mode_1}")

    # 3. Test Mode 2: Personalized Daily Report ("Your Day" Card)
    print("\n--- Testing Mode 2: Personalized Daily Report ---")
    allocation_payload = {
        "user_id": "u_042",
        "resource": "Gym",
        "usual_time": "19:00",
        "predicted_occupancy": "95%",
        "assigned_alternative": "18:30",
        "reason": "Batch-balanced to avoid overloading 19:00 slot"
    }
    response_mode_2 = rag.generate_personalized_report(allocation_payload)
    print(f"Copilot Output:\n{response_mode_2}")

if __name__ == "__main__":
    run_test()