# Basic usage with defaults
result = load_model_via_api("mythomakisemerged-13b.Q5_K_S.gguf")
if result["success"]:
    print(f"Successfully loaded {result['model']}")
else:
    print(f"Failed to load model: {result['error']}")

# Custom parameters
result = load_model_via_api(
    "another-model.gguf",
    n_gpu_layers=40,
    n_ctx=8192,
    temperature=0.7
)

# Custom API endpoint
result = load_model_via_api(
    "custom-model",
    api_url="http://localhost:1234/v1/model/load"
)
