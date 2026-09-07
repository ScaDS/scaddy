## changelog:

- VLM addition / fallback: if scaddy gets a picture a vlm in parallel describes it and gives image description to answer context; this is useful whenever scaddy doesn't recognize image content.
- CAG (cache augmented generation): when a new chat starts, all scads.ai & living lab knowledge is fed into context of the model/conversation. This replaces RAG and simplifies knowledge management.
- added admin page

## to do:

- UI:
  - reset btn unstable: whenever chat was active, sometimes the frontend needs a reload and ws-reconnect to trigger /reset route. Don't know why?
  - text underneath animation is overflowing. Needs to be fixed.
- local model is okay in conversation but features/tools like CAG aren't stable right now. Check again; LLM-Inferenz currently is OpenAI-API (GPT-4o-mini). 
  

## future:

- change behavior in vision mode by first taking the picture an then asking what AI can see there; currently it is first waiting for the question/speaking and then taking the image when sending the question; this could possible end in a confused user because the user already thought of taking an image and lost focus of the object the user wanted to capture
- help btns in every mode?
