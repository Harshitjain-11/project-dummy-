# import numpy as np

# class IntentPredictor:
#     def __init__(self, model_loader, threshold=0.45):
#         """
#         Intent predictor handles model predictions and confidence threshold.
#         """
#         self.model_loader = model_loader
#         self.model = model_loader.model
#         self.label_encoder = model_loader.label_encoder
#         self.intents = model_loader.intents
#         self.threshold = threshold

#     def predict(self, message: str):
#         """
#         Predict intent tag and confidence using the trained pipeline.
#         """
#         if not message or not self.model:
#             return "fallback", 0.0

#         # Use pipeline directly
#         probs = self.model.predict_proba([message.lower().strip()])[0]
#         best_idx = int(np.argmax(probs))
#         conf = float(probs[best_idx])

#         tag = self.label_encoder.inverse_transform([best_idx])[0]
#         if conf < self.threshold:
#             return "fallback", conf

#         return str(tag), conf
# chatbot/intent_predictor.py
import numpy as np

class IntentPredictor:
    def __init__(self, model_loader, threshold: float = 0.35):
        """
        model_loader: instance of ModelLoader (has predict_proba and decode_label)
        threshold: confidence threshold (0-1) — lower if dataset is small
        """
        self.loader = model_loader
        self.threshold = float(threshold)
        # keep intents from model_loader if you want to access responses here
        self.intents = getattr(model_loader, "intents", None)

    def predict(self, text: str):
        """
        Returns (tag, confidence). Tag is 'fallback' if confidence < threshold.
        """
        if not text or not text.strip():
            return "fallback", 0.0

        text = text.strip()
        # get probability vector from pipeline
        probs = self.loader.predict_proba([text])[0]   # shape: (n_classes,)
        best_pos = int(np.argmax(probs))               # index position in model.classes_
        conf = float(probs[best_pos])

        # decode actual tag string
        tag = self.loader.decode_label(best_pos)

        if conf < self.threshold:
            return "fallback", conf

        return tag, conf
