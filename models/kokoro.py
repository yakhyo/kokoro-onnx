import torch
import numpy as np
import onnxruntime as ort

TOKEN_LIMIT = 510
SAMPLE_RATE = 24_000


class Kokoro:
    def __init__(self, model_path: str, style_vector_path: str, tokenizer, lang: str = 'en-us') -> None:
        """
        Initializes the ONNXInference class.

        Args:
            model_path (str): Path to the ONNX model file.
            style_vector_path (str): Path to the style vector file.
            lang (str): Language code for the tokenizer.
        """
        self.sess = ort.InferenceSession(model_path)
        self.style_vector_path = style_vector_path
        self.tokenizer = tokenizer
        self.lang = lang

    def preprocess(self, text):
        """
        Converts input text to tokenized numerical IDs and loads the style vector.

        Args:
            text (str): Input text to preprocess.

        Returns:
            tuple: Tokenized input and corresponding style vector.
        """
        # Convert text to phonemes and tokenize
        phonemes = self.tokenizer.phonemize(text, lang=self.lang)
        tokenized_phonemes = self.tokenizer.tokenize(phonemes)

        if not tokenized_phonemes:
            raise ValueError("No tokens found after tokenization")

        style_vector = torch.load(self.style_vector_path, weights_only=True)

        if len(tokenized_phonemes) > TOKEN_LIMIT:
            token_chunks = self.split_into_chunks(tokenized_phonemes)

            tokens_list = []
            styles_list = []

            for chunk in token_chunks:
                token_chunk = [[0, *chunk, 0]]
                style_chunk = style_vector[len(chunk)].numpy()

                tokens_list.append(token_chunk)
                styles_list.append(style_chunk)

            return tokens_list, styles_list

        style_vector = style_vector[len(tokenized_phonemes)].numpy()
        tokenized_phonemes = [[0, *tokenized_phonemes, 0]]

        return tokenized_phonemes, style_vector

    @staticmethod
    def split_into_chunks(tokens):
        """
        Splits a list of tokens into chunks of size TOKEN_LIMIT.

        Args:
            tokens (list): List of tokens to split.

        Returns:
            list: List of token chunks.
        """
        tokens_chunks = []
        for i in range(0, len(tokens), TOKEN_LIMIT):
            tokens_chunks.append(tokens[i:i+TOKEN_LIMIT])
        return tokens_chunks

    def infer(self, tokens, style_vector, speed=1.0):
        """
        Runs inference using the ONNX model.

        Args:
            tokens (list): Tokenized input for the model.
            style_vector (numpy.ndarray): Style vector for the model.
            speed (float): Speed parameter for inference.

        Returns:
            numpy.ndarray: Generated audio data.
        """
        # Perform inference
        audio = self.sess.run(
            None,
            {
                'tokens': tokens,
                'style': style_vector,
                'speed': np.array([speed], dtype=np.float32),
            }
        )[0]
        return audio

    def generate_audio(self, text,  speed=1.0):
        """
        Full pipeline: preprocess, infer, and save the generated audio.

        Args:
            text (str): Input text to generate audio from.
            speed (float): Speed parameter for inference.
        """
        # Preprocess text
        tokenized_data, styles_data = self.preprocess(text)

        audio_segments = []
        if len(tokenized_data) > 1:  # list of token chunks
            for token_chunk, style_chunk in zip(tokenized_data, styles_data):
                audio = self.infer(token_chunk, style_chunk, speed=speed)
                audio_segments.append(audio)
        else:  # single token less than input limit
            # Run inference
            audio = self.infer(tokenized_data, styles_data, speed=speed)
            audio_segments.append(audio)

        full_audio = np.concatenate(audio_segments)

        return full_audio, SAMPLE_RATE
