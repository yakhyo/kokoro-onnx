import soundfile as sf

from models import Tokenizer, Kokoro


def main():
    model_path = "weights/kokoro-v0_19.onnx"
    style_vector_path = "voices/af.pt"
    output_filename = "test_out.wav"
    tokenizer = Tokenizer()

    text = (
        "This approach ensures the entire text is processed without exceeding the token limit and outputs seamless audio for the full input. Let me know if you need further assistance!"
    )

    inference = Kokoro(model_path, style_vector_path, tokenizer=tokenizer, lang='en-us')
    audio, sample_rate = inference.generate_audio(text, speed=1.0)

    # Save the audio to a file
    sf.write(output_filename, audio, sample_rate)
    print(f"Audio saved to {output_filename}")


if __name__ == "__main__":
    main()
