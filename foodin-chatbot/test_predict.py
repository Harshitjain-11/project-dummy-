from chatbot.model_loader import ModelLoader

# Load model
loader = ModelLoader()

print("\n==============================")
print("🤖  Chatbot Model Tester")
print("==============================")
print("Loaded classes:", loader.decoded_classes())
print("==============================\n")

def print_top_n(prob_row, n=5):
    """
    Pretty print top-N intents with confidence bars.
    """
    classes = loader.model.classes_
    decoded = loader.decoded_classes()

    paired = list(zip(range(len(prob_row)), prob_row))
    paired.sort(key=lambda x: x[1], reverse=True)

    print("\n🔝 Top predictions:")
    for idx, p in paired[:n]:
        tag = decoded[idx] if idx < len(decoded) else "?"
        bar = "█" * int(p * 20)
        print(f" - {tag:20s}  {p:.4f}  {bar}")

    print()

while True:
    text = input("Type something (or press Enter to quit): ").strip()
    if not text:
        break

    # Model prediction
    probs = loader.predict_proba([text])[0]

    # Best prediction
    best_pos = probs.argmax()
    conf = float(probs[best_pos])
    best_tag = loader.decode_label(best_pos)

    print("\n======================================")
    print(f"🧠 Predicted intent : {best_tag}")
    print(f"🔢 Confidence       : {conf:.4f}")
    print("--------------------------------------")

    # Print top-N predictions
    print_top_n(probs, n=5)

    # Debug info (optional)
    print("📊 Raw model classes:", list(loader.model.classes_))
    print("📝 Decoded classes  :", loader.decoded_classes())
    print("======================================\n")
