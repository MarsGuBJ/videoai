from src.onnx_resource import OnnxResource
from src.config import config


def run_infer():
    onnx_resource = OnnxResource(
        config.model_path,
        providers=getattr(config, "providers", None),
    )
    onnx_resource.infer()
    onnx_resource.release_resource()


if __name__ == "__main__":
    run_infer()
