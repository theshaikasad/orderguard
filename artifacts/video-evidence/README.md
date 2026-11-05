# Video provenance and verification

The finished film is `../orderguard-hackathon-demo.mp4`. It uses actual Playwright recordings of the running local OrderGuard application, synthetic customer messages, and genuine Meta Muse inference. No model response was substituted or mocked for the film.

Fresh recording: `real-muse-recording.json` contains the five actual backend responses and recording timestamps: clarification, ₹900 quote, eggless/floral repricing to ₹1,300, natural acceptance, and a late flavor change after an explicit owner production action. All five interpretation and reply sources were `meta`. Customer/seller recordings were captured concurrently from the same persisted conversation. The film uses the fresh clarification, quote, revision and acceptance footage.

Scenario Lab, Bloom onboarding history and the ₹859/₹959 florist conversations are recordings of previously verified, persisted real Muse results. The film labels them accordingly. Relevant earlier evidence is in `artifacts/submission`, `artifacts/m3`, `artifacts/m4`, and `M3_REPORT.md`. Their original history was not rewritten.

Editorial elements are titles, original graphics, transitions, tight crops, subtitles, held frames, accelerated model waits, local macOS Samantha narration, and an original locally synthesized quiet ambient bed. Synthetic customer conversations and shortened waiting time are visibly disclosed. Instagram is not live; no customer sends, payments or deployment are implied.

Verification: ffprobe confirms H.264, 1920×1080, 30 fps, AAC audio and an English subtitle track, duration 164.77 seconds. Burned-in subtitles are also included. Full decode passed; no sustained black interval of 0.5 seconds or more was detected. Eleven representative frames were extracted and inspected for text clipping and legibility. Measured audio mean is -16.1 dB and peak is -0.8 dB. Narration follows scene-specific generated audio and subtitle intervals.

Raw browser videos, intermediate parts, narration and first working exports are retained locally under the ignored `artifacts/video-production/` directory. The renderer validates a candidate before replacing the final file and preserves the preceding working export. No unlisted upload was attempted because the owner requested file delivery only.
