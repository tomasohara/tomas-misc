#! /usr/bin/env python
#
# Uses the Hugging Face API for automatic speech recognition (ASR).
#
# Based on following:
# https://stackoverflow.com/questions/71568142/how-can-i-extract-and-store-the-text-generated-from-an-automatic-speech-recognit # pylint: disable=line-too-long
#
# TODO:
# - Add chunking to handle large file:
#     https://huggingface.co/blog/asr-chunking
#

"""Speech recognition via Hugging Face"""

# Standard modules
# TODO: import re

# Intalled module
## OLD: import gradio as gr
## BAD: import torch
## TODO:
## from transformers import pipeline

# Local modules
from mezcla import debug
from mezcla.main import Main
from mezcla import system
from mezcla import glue_helpers as gh

# Constants
TL = debug.TL

## TODO:
## # Environment options
## # Notes:
## # - These are just intended for internal options, not for end users.
## # - They also allow for enabling options in one place rather than four
## #   when using main.Main (e.g., [Main member] initialization, run-time
## #   value, and argument spec., along with string constant definition).
## #
## ENABLE_FUBAR = system.getenv_bool("ENABLE_FUBAR", False,
##                                   description="Enable fouled up beyond all recognition processing")

ASR_TASK = "automatic-speech-recognition"
# TODO: WHISPER = getenv...("whisper-large"); DEFAULT_MODEL = ...
DEFAULT_MODEL = "facebook/s2t-medium-librispeech-asr"
ASR_MODEL = system.getenv_text(
    "ASR_MODEL", DEFAULT_MODEL,
    description="Hugging Face model for ASR")
# OLD: USE_CPU = system.getenv_bool("USE_CPU", False, description="Uses Torch on CPU if True")
# OLD: TORCH_DEVICE_DEFAULT = ("cpu" if USE_CPU else "cuda")
USE_GPU = system.getenv_bool("USE_GPU", False, description="Uses Torch on GPU if True")
TORCH_DEVICE_DEFAULT = ("cuda" if USE_GPU else "cpu")
TORCH_DEVICE = system.getenv_text(
    "TORCH_DEVICE", TORCH_DEVICE_DEFAULT,
    description="Torch device to use")

#-------------------------------------------------------------------------------

SOUND_FILE = system.getenv_text("SOUND_FILE", "fuzzy-testing-1-2-3.wav",
                                "Audio file with speech to recognize")
USE_INTERFACE = system.getenv_bool("USE_INTERFACE", False,
                                   "Use web-based interface via gradio")

# Optionally load UI support
gr = None   # pylint: disable=invalid-name
if USE_INTERFACE:
    import gradio as gr                 # pylint: disable=import-error


def main():
    """Entry point"""
    debug.trace(TL.USUAL, f"main(): script={system.real_path(__file__)}")

    # Show simple usage if --help given
    dummy_app = Main(description=__doc__, skip_input=False, manual_input=False)

    # Resolve path for file
    sound_file = SOUND_FILE
    if not system.file_exists(sound_file):
        script_dir = gh.dirname(__file__)
        sound_file = gh.resolve_path(SOUND_FILE, base_dir=script_dir)
    if not system.file_exists(sound_file):
        system.exit(f"Error: unable to find SOUND_FILE '{sound_file}'")

    ## TEMP:
    ## pylint: disable=import-outside-toplevel
    from transformers import pipeline
    import torch
    ## BAD:
    ## model = pipeline(task="automatic-speech-recognition",
    ##                  model="facebook/s2t-medium-librispeech-asr")
    ## OLD: model = pipeline(task=ASR_TASK, model=ASR_MODEL)

    device = torch.device(TORCH_DEVICE)
    model = pipeline(task=ASR_TASK, model=ASR_MODEL, device=device)

    if USE_INTERFACE:
        pipeline_if = gr.Interface.from_pipeline(
            model,
            title="Automatic Speech Recognition (ASR)",
            ## OLD: description="Using pipeline with Facebook S2T for ASR.",
            description="Using pipeline with default",
            examples=[sound_file])
        pipeline_if.launch()
    else:
        ## OLD: Prints dictionary {"text": "TRANSLATED_CONTENT"}
        # print(model(sound_file))
        print((model(sound_file))["text"])
    # return

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
