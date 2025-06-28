import os
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('textcleaner.log'),
        logging.StreamHandler()
    ]
)

class TextCleaner:
    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
        self.logger = logging.getLogger(__name__)
        self.logger.info(f'Initialized TextCleaner for input: {input_file}, output: {output_file}')

    def preprocess(self):
        self.logger.info(f'Beginning of file processing {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
                text = text.replace('\n', ' ')
                text = re.sub(r' +', ' ', text).strip()


                

            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(text)


            self.logger.info(f'End of the line {self.output_file}')
        except Exception as e:
            self.logger.error(f'A fucking error: {e}', exc_info=True)
