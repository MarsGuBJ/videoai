import onnxruntime as ort


class ModelInspector:
    def __init__(self, providers=None):
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        available = ort.get_available_providers()
        self.providers = [p for p in providers if p in available]
        if not self.providers:
            raise RuntimeError(f"No requested providers available; have {available}")
        self.session = None

    def load_model(self, model_path):
        print(f">>> Load ONNX: {model_path}")
        self.session = ort.InferenceSession(model_path, providers=self.providers)

    def print_input_info(self):
        print("\n==================== INPUT INFO ====================")
        inputs = self.session.get_inputs()
        print(f"Number of inputs = {len(inputs)}\n")

        for i, inp in enumerate(inputs):
            print(f"Input[{i}]")
            print(f"  name      : {inp.name}")
            print(f"  shape     : {inp.shape}")
            print(f"  data_type : {inp.type}")
            print("----------------------------------------------------")

        print("\n==================== OUTPUT INFO ====================")
        outputs = self.session.get_outputs()
        print(f"Number of outputs = {len(outputs)}\n")
        for i, out in enumerate(outputs):
            print(f"Output[{i}]")
            print(f"  name      : {out.name}")
            print(f"  shape     : {out.shape}")
            print(f"  data_type : {out.type}")
            print("----------------------------------------------------")


if __name__ == "__main__":
    model_path = "/workspace/dino_image_infer/model/dino_smoke_v1.onnx"

    inspector = ModelInspector()
    inspector.load_model(model_path)
    inspector.print_input_info()
