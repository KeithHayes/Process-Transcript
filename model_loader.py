import requests
import json

def load_model_via_api(
    model_name: str,
    api_url: str = "http://localhost:5000/v1/internal/model/load",
    timeout: int = 40,
    n_gpu_layers: int = 32,
    n_ctx: int = 4096,
    **extra_args
) -> dict:
    """
    Loads a model via API with configurable parameters.
    
    Args:
        model_name: Name of the model to load
        api_url: URL of the model loading endpoint
        timeout: Request timeout in seconds
        n_gpu_layers: Number of GPU layers to use (for GGUF models)
        n_ctx: Context length (for GGUF models)
        extra_args: Additional arguments to pass to the model loader
        
    Returns:
        Dictionary containing:
        - success: bool indicating overall success
        - model: model name attempted to load
        - response: full API response if available
        - error: error message if any
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
