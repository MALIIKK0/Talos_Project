from agent import create_orchestrator
from IPython.display import Image, display
orchestrator = create_orchestrator()
# display(Image(orchestrator.get_graph().draw_mermaid_png()))
# png_bytes = orchestrator.get_graph().draw_mermaid_png()

# with open("orchestrator_graph.png", "wb") as f:
#     f.write(png_bytes)