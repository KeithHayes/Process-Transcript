def savechunk(self):
    try:
        if not self.chunk:
            return
            
        self.logger.debug(f'Saving chunk')
        target_pointer = self.output_pointer
        chunkwords = [word for word in self.chunk.split(' ') if word]
        
        # Always save all remaining words if we're at the end of input
        if self.input_word_pointer >= len(self.input_array):
            save_words = chunkwords
        else:
            save_words = chunkwords[:OUTPUT_CHUNK_SIZE]  # First 150 words or fewer
            
        if save_words:
            save_words_string = ' '.join(save_words) + ' '
            self.output_string += save_words_string
            self.output_pointer += len(save_words_string)
            
        # Only keep overlap if there's more input to process
        if self.input_word_pointer < len(self.input_array):
            remaining_words = chunkwords[OUTPUT_CHUNK_SIZE:] if len(chunkwords) > OUTPUT_CHUNK_SIZE else []
            remaining_words_string = ' '.join(remaining_words)
            remaining_words_string = re.sub(r"[\.!?](?!.*[\.!?])", '', remaining_words_string)
            remaining_words_string = re.sub(r"[A-Z](?!.*[A-Z])", '', remaining_words_string)
            self.chunk = remaining_words_string + ' '
        else:
            self.chunk = ''  # Clear chunk when we're done
            
        self.logger.debug(f'Saved {len(save_words)} words to output, {len(self.chunk.split())} words remaining in chunk')
        
    except Exception as e:
        self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
        raise