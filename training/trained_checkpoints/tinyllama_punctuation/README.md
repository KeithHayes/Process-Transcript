---
library_name: peft
tags:
- axolotl
- base_model:adapter:/media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0
- lora
- transformers
datasets:
- /home/kdog/pythonprojects/process_transcript/training/datasets/augmented_dataset.jsonl
pipeline_tag: text-generation
base_model: /media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0
model-index:
- name: home/kdog/pythonprojects/process_transcript/training/trained_checkpoints/tinyllama_punctuation
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

[<img src="https://raw.githubusercontent.com/axolotl-ai-cloud/axolotl/main/image/axolotl-badge-web.png" alt="Built with Axolotl" width="200" height="32"/>](https://github.com/axolotl-ai-cloud/axolotl)
<details><summary>See axolotl config</summary>

axolotl version: `0.12.0.dev0`
```yaml
base_model: /media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0
model_config_type: llama
tokenizer_type: AutoTokenizer
trust_remote_code: true

# Quantization
load_in_4bit: true
use_qlora: true
adapter: qlora
lora_r: 8
lora_alpha: 16
lora_target_modules: "all-linear"
lora_dropout: 0.05
bnb_4bit_compute_dtype: float16
bnb_4bit_quant_type: nf4
bnb_4bit_use_double_quant: true
fp16: true

# Dataset
datasets:
  - path: /home/kdog/pythonprojects/process_transcript/training/datasets/augmented_dataset.jsonl
    type: alpaca
    dataset_prepared_path: /home/kdog/pythonprojects/process_transcript/training/datasets/prepared
    field_mapping:
      instruction: "instruction"
      input: "input"
      output: "output"

# Training
output_dir: /home/kdog/pythonprojects/process_transcript/training/trained_checkpoints/tinyllama_punctuation
num_epochs: 5
learning_rate: 1e-5
lr_scheduler: cosine
warmup_steps: 50
optimizer: adamw_torch
weight_decay: 0.01

# Memory
sequence_len: 300
micro_batch_size: 1
gradient_accumulation_steps: 4
gradient_checkpointing: true
train_on_inputs: false
add_eos_token: true

# Logging/Saving
logging_steps: 10
save_strategy: steps
save_steps: 200
save_total_limit: 2
eval_steps: 200
eval_strategy: steps
preprocessing_num_workers: 1  # Start low
dataloader_num_workers: 2
group_by_length: true
```

</details><br>

# home/kdog/pythonprojects/process_transcript/training/trained_checkpoints/tinyllama_punctuation

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
- learning_rate: 1e-05
- train_batch_size: 1
- eval_batch_size: 1
- seed: 42
- gradient_accumulation_steps: 4
- total_train_batch_size: 4
- optimizer: Use adamw_torch with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- lr_scheduler_warmup_steps: 50
- training_steps: 82
- mixed_precision_training: Native AMP

### Training results



### Framework versions

- PEFT 0.17.0
- Transformers 4.54.1
- Pytorch 2.6.0+cu124
- Datasets 4.0.0
- Tokenizers 0.21.4