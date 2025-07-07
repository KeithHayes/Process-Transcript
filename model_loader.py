import requests
import json

def load_model_via_api(
    model_name: str,
    api_url: str = "http://localhost:5000/v1/internal/model/load",
    timeout: int = 40,
    n_gpu_layers: int = 41,
    n_ctx: int = 4096,
    **extra_args
) -> dict:
    """
    Loads a model via API with configurable parameters.

    """
    load_params = {
        "model_name": model_name,
        "args": {
            "n_gpu_layers": n_gpu_layers,
            "n_ctx": n_ctx,
            **extra_args
        }
    }

    try:
        response = requests.post(
            api_url,
            json=load_params,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        response.raise_for_status()

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"message": response.text.strip()}

        return {
            "success": True,
            "model": model_name,
            "response": response_data
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "model": model_name,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "model": model_name,
            "error": f"Unexpected error: {str(e)}"
        }

def main(model_to_load: str):
    """
    Main function to initiate model loading via API.

    Args:
        model_to_load: The name of the model to be loaded.
    """
    print(f"Attempting to load model: {model_to_load}")

    # --- PARAMETER ADJUSTMENTS HERE ---
    # Adjust n_gpu_layers and n_ctx based on your system's VRAM
    # and the model's requirements.

    # Default/Conservative settings
    gpu_layers = 41  
    ctx_size = 4096

    load_result = load_model_via_api(
        model_name=model_to_load,
        n_gpu_layers=gpu_layers,
        n_ctx=ctx_size
    )

    if load_result["success"]:
        print(f"Successfully loaded model: {load_result['model']}")
        print("API Response:", json.dumps(load_result["response"], indent=2))
    else:
        print(f"Failed to load model: {load_result['model']}")
        print("Error:", load_result["error"])
        if "response" in load_result:
            print("API Response (if available):", json.dumps(load_result["response"], indent=2))

if __name__ == "__main__":
    model_name_to_load = "mythomakisemerged-13b.Q5_K_S.gguf"
    main(model_name_to_load)