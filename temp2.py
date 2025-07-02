def savechunk(self):
    try:
        if not self.chunk:
            return
        self.logger.debug(f'Saving chunk')
        target_pointer = self.output_pointer
        chunkwords = [word for word in self.chunk.split(' ') if word]
        save_words = chunkwords[:150]                                   # First 150 words of chunk of chunk or fewer
        if save_words:
            save_words_string = ' '.join(save_words) + ' '              # Join with spaces, add space at end
            self.output_string += save_words_string
            self.output_pointer += len(save_words_string)
            
        remaining_words = chunkwords[150:] if len(chunkwords) > 150 else []
        remaining_words_string = ' '.join(remaining_words)
        remaining_words_string = re.sub(r"[\.!?](?!.*[\.!?])", '', remaining_words_string)
        remaining_words_string = re.sub(r"[A-Z](?!.*[A-Z])", '', remaining_words_string)
        self.chunk = remaining_words_string + ' '
            
        self.logger.debug(f'Saving chunk at: {target_pointer}, length: {self.output_pointer - target_pointer} characters')
    except Exception as e:
        self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
        raise