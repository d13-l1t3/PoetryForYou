# Dynamic View — Voice Search Sequence

## Sequence Diagram

![Voice Search Sequence](voice-search-sequence.puml)

> To render: paste `voice-search-sequence.puml` into [plantuml.com](https://www.plantuml.com/plantuml/uml/).

## Scenario Description

This diagram shows the most complex request flow in the system: a user sends a voice message while in `/search` mode. It involves:

1. **Bot** downloads the voice file from Telegram
2. **Backend** receives the audio via `POST /voice`
3. **Whisper STT** transcribes the audio to text
4. **Backend** checks user stage (`searching`) and skips LLM intent classification
5. **LLM** extracts search keywords from the transcribed text
6. **Poem Source** searches hardcoded and external poem databases
7. Results are returned to the user

## Timing Measurement

Measured in production (VPS: 1 vCPU, 2 GB RAM):

| Step | Time |
|------|------|
| Voice download from Telegram | ~200ms |
| Whisper transcription (5s audio, `small` model) | ~3-5s |
| Keyword extraction (LLM) | ~500-1000ms |
| Poem search (hardcoded + external) | ~100-500ms |
| **Total end-to-end** | **~4-7 seconds** |

The bottleneck is Whisper transcription on CPU. Using the `tiny` model would reduce this to ~1-2s but with lower accuracy.
