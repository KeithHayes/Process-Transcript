---
library_name: peft
tags:
- generated_from_trainer
datasets:
- /home/kdog/pythonprojects/process_transcript/training/datasets/augmented_dataset.jsonl
base_model: /media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0
model-index:
- name: model-out
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

[<img src="https://raw.githubusercontent.com/axolotl-ai-cloud/axolotl/main/image/axolotl-badge-web.png" alt="Built with Axolotl" width="200" height="32"/>](https://github.com/axolotl-ai-cloud/axolotl)
<details><summary>See axolotl config</summary>

axolotl version: `0.11.0`
```yaml
base_model: /media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0
model_type: llama
tokenizer_type: AutoTokenizer
trust_remote_code: false

# QLoRA Configuration
adapter: qlora
load_in_4bit: true
use_qlora: true

# 4-bit Quantization
bnb_4bit_compute_dtype: float16
bnb_4bit_quant_type: nf4
bnb_4bit_use_double_quant: true

# LoRA Parameters
lora_r: 64
lora_alpha: 128
lora_target_modules: ["q_proj", "v_proj"]
lora_dropout: 0.1

# Batch Configuration
micro_batch_size: 1
gradient_accumulation_steps: 8

# Training Schedule
max_steps: 10800
learning_rate: 2.5e-5
lr_scheduler_type: cosine
warmup_ratio: 0.05
max_grad_norm: 0.5

# Dataset - UPDATED SECTION
datasets:
  - path: /home/kdog/pythonprojects/process_transcript/training/datasets/augmented_dataset.jsonl
    type: alpaca  # Changed from json to alpaca
    dataset_prepared_path: /home/kdog/pythonprojects/process_transcript/training/datasets/prepared

# System Configuration
fp16: true
gradient_checkpointing: true
optim: adamw_torch
weight_decay: 0.01

# Logging/Saving
save_strategy: steps
save_steps: 500
logging_steps: 20
```

</details><br>

# model-out

This model was trained from scratch on the /home/kdog/pythonprojects/process_transcript/training/datasets/augmented_dataset.jsonl dataset.

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 2.5e-05
- train_batch_size: 1
- eval_batch_size: 1
- seed: 42
- gradient_accumulation_steps: 8
- total_train_batch_size: 8
- optimizer: Use adamw_torch_fused with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- training_steps: 10800
- mixed_precision_training: Native AMP

### Training results



### Framework versions

- PEFT 0.15.2
- Transformers 4.53.1
- Pytorch 2.6.0+cu124
- Datasets 3.6.0
- Tokenizers 0.21.4