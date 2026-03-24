# User Acceptance Tests

## UAT-1: Onboarding Flow

**Related acceptance criteria**: User can start the bot and select a language.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Send `/start` to the bot | Bot greets and asks to choose language (ru/en/mix) |
| 2 | Send `en` | Bot confirms "✅ Language: EN" and shows main menu |
| 3 | Send `/help` | Bot shows available commands in English |

**Result**: ✅ Passed

---

## UAT-2: Library Browsing

**Related acceptance criteria**: User can browse poems by category and author.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Complete onboarding (ru) | Main menu shown |
| 2 | Send `/library` | Bot shows poem library with categories |
| 3 | Select a category | Bot shows poems in that category |
| 4 | Select a poem | Bot starts the learning session |

**Result**: ✅ Passed

---

## UAT-3: Poem Learning (Chunk-Based)

**Related acceptance criteria**: User can learn a poem in chunks with spaced repetition.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select a poem from library | Bot shows first chunk of the poem |
| 2 | Try to reproduce the chunk from memory | Bot checks accuracy and gives feedback |
| 3 | Complete all chunks | Bot marks poem as learned, awards points |

**Result**: ✅ Passed

---

## UAT-4: Voice Search (NEW — MVP v2)

**Related acceptance criteria**: User can search for poems using voice messages.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Complete onboarding | Main menu shown |
| 2 | Send `/search` | Bot asks what to search for |
| 3 | Send a voice message saying "Пушкин У лукоморья" | Bot transcribes voice and shows matching poems |
| 4 | Select a poem from results | Bot starts learning session for that poem |

**Result**: ✅ Passed

---

## UAT-5: Review Learned Poems (NEW — MVP v2)

**Related acceptance criteria**: User can review previously learned poems using spaced repetition.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Learn at least one poem | Poem marked as learned |
| 2 | Send `/review` | Bot shows poem for review |
| 3 | Try to reproduce from memory | Bot scores the attempt and updates spaced repetition schedule |

**Result**: ✅ Passed
