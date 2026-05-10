 FINAL CLEAN README (READY TO PASTE ✅)
👉 Replace your README completely with THIS 👇

Markdown# 🚀 PlayReady GenAI QA Automation Framework## 📌 OverviewThis repository implements a **GenAI QA Automation framework** for validating a **PlayReady Foundry-based RAG chatbot**.The framework automates:- Agent query execution- Evaluation dataset generation- Quality assessment using RAGAS & Foundry evaluation- Scalable test execution> ⚠️ This reflects the **current implementation**. DeepEval, dashboards, and observability are planned enhancements.---## 🎯 Objectives- Validate responses for correctness, relevance, grounding- Detect hallucinations and edge-case failures- Enable large-scale automated testing- Support reproducible QA workflows- Build foundation for **EvalOps-style GenAI testing**---## ✅ Current Capabilities### 🔹 Foundry Agent Execution```bashpython scripts/query_new_agent.pyShow less

Calls real Foundry agent
Generates evaluation-ready dataset


🔹 RAGAS Evaluation
Shellpython scripts/run_ragas_bridge.pyShow more lines
Metrics:

Faithfulness
Answer Relevancy
Context Precision
Context Recall


🔹 Foundry Evaluation Layer

foundry_layer/foundry_evaluator.py
tests/test_foundry_eval.py

Supports additional evaluation signals.

🔹 Multi-Suite Testing
Covers:

Negative scenarios
Conversational flows
Edge cases
Compliance / data safety


🔹 Slot-Based Execution (Scalable)
Shellpowershell scripts/run_bridge_in_slots.ps1Show more lines

Prevents timeouts
Enables batch processing


🔹 CI/CD Ready

azure-pipelines.yml
reproducible QA workflows


🧠 Architecture (Current)
flowchart TD    A[Test Cases] --> B[query_new_agent.py]    B --> C[Evaluation Dataset]    C --> D[RAGAS Evaluation]    C --> E[Foundry Evaluation]    D --> F[RAGAS Results]    E --> G[Foundry Results]    F --> H[Reports / Analysis]    G --> H    H --> I[QA Review / Bug Analysis]Show more lines#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 {font-family:"trebuchet ms", verdana, arial, sans-seriffont-size:16px;fill:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-animation-slow {stroke-dashoffset:900animation-duration:50s;animation-timing-function:linear;animation-delay:0s;animation-iteration-count:infinite;animation-direction:normal;animation-fill-mode:none;animation-play-state:running;animation-name:dash;animation-timeline:auto;animation-range-start:normal;animation-range-end:normal;stroke-linecap:round;stroke-dasharray:9, 5;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-animation-fast {stroke-dashoffset:900animation-duration:20s;animation-timing-function:linear;animation-delay:0s;animation-iteration-count:infinite;animation-direction:normal;animation-fill-mode:none;animation-play-state:running;animation-name:dash;animation-timeline:auto;animation-range-start:normal;animation-range-end:normal;stroke-linecap:round;stroke-dasharray:9, 5;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .error-icon {fill:rgb(85, 34, 34)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .error-text {fill:rgb(85, 34, 34)stroke:rgb(85, 34, 34);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-normal {stroke-width:1px}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-thick {stroke-width:3.5px}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-solid {stroke-dasharray:0}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-invisible {stroke-width:0fill:none;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-dashed {stroke-dasharray:3}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-dotted {stroke-dasharray:2}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .marker {fill:rgb(51, 51, 51)stroke:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .marker.cross {stroke:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 svg {font-family:"trebuchet ms", verdana, arial, sans-seriffont-size:16px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 p {margin-top:0pxmargin-right:0px;margin-bottom:0px;margin-left:0px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label {font-family:"trebuchet ms", verdana, arial, sans-serifcolor:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label text {fill:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label span {color:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label span p {background-color:transparent}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label text, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 span {fill:rgb(51, 51, 51)color:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node rect, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node circle, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node ellipse, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node polygon, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node path {fill:rgb(236, 236, 255)stroke:rgb(147, 112, 219);stroke-width:1px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .rough-node .label text, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label text, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape .label, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape .label {text-anchor:middle}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .katex path {fill:rgb(0, 0, 0)stroke:rgb(0, 0, 0);stroke-width:1px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .rough-node .label, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape .label, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape .label {text-align:center}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node.clickable {cursor:pointer}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .root .anchor path {stroke-width:0stroke:rgb(51, 51, 51);fill:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .arrowheadPath {fill:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgePath .path {stroke:rgb(51, 51, 51)stroke-width:2px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .flowchart-link {stroke:rgb(51, 51, 51)fill:none;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel {background-color:rgba(232, 232, 232, 0.8)text-align:center;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel p {background-color:rgba(232, 232, 232, 0.8)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel rect {opacity:0.5background-color:rgba(232, 232, 232, 0.8);fill:rgba(232, 232, 232, 0.8);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .labelBkg {background-color:rgba(232, 232, 232, 0.5)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster rect {fill:rgb(255, 255, 222)stroke:rgb(170, 170, 51);stroke-width:1px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster text {fill:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster span {color:rgb(51, 51, 51)}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 div.mermaidTooltip {position:absolutetext-align:center;max-width:200px;padding-top:2px;padding-right:2px;padding-bottom:2px;padding-left:2px;font-family:"trebuchet ms", verdana, arial, sans-serif;font-size:12px;background-image:initial;background-position-x:initial;background-position-y:initial;background-size:initial;background-repeat:initial;background-attachment:initial;background-origin:initial;background-clip:initial;background-color:rgb(249, 255, 236);border-top-width:1px;border-right-width:1px;border-bottom-width:1px;border-left-width:1px;border-top-style:solid;border-right-style:solid;border-bottom-style:solid;border-left-style:solid;border-top-color:rgb(170, 170, 51);border-right-color:rgb(170, 170, 51);border-bottom-color:rgb(170, 170, 51);border-left-color:rgb(170, 170, 51);border-image-source:initial;border-image-slice:initial;border-image-width:initial;border-image-outset:initial;border-image-repeat:initial;border-top-left-radius:2px;border-top-right-radius:2px;border-bottom-right-radius:2px;border-bottom-left-radius:2px;pointer-events:none;z-index:100;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .flowchartTitleText {text-anchor:middlefont-size:18px;fill:rgb(51, 51, 51);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 rect.text {fill:nonestroke-width:0;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape {background-color:rgba(232, 232, 232, 0.8)text-align:center;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape p, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape p {background-color:rgba(232, 232, 232, 0.8)padding-top:2px;padding-right:2px;padding-bottom:2px;padding-left:2px;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape rect, #mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape rect {opacity:0.5background-color:rgba(232, 232, 232, 0.8);fill:rgba(232, 232, 232, 0.8);}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label-icon {display:inline-blockheight:1em;overflow-x:visible;overflow-y:visible;vertical-align:-0.125em;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label-icon path {fill:currentcolorstroke:revert;stroke-width:revert;}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 :root {--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif}
#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .error-icon{fill:#552222;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .error-text{fill:#552222;stroke:#552222;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-normal{stroke-width:1px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-thick{stroke-width:3.5px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-solid{stroke-dasharray:0;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .marker{fill:#333333;stroke:#333333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .marker.cross{stroke:#333333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 svg{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 p{margin:0;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label{font-family:"trebuchet ms",verdana,arial,sans-serif;color:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label text{fill:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label span{color:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster-label span p{background-color:transparent;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label text,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 span{fill:#333;color:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node rect,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node circle,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node ellipse,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node polygon,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node path{fill:#ECECFF;stroke:#9370DB;stroke-width:1px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .rough-node .label text,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label text,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape .label,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape .label{text-anchor:middle;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .rough-node .label,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape .label,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape .label{text-align:center;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node.clickable{cursor:pointer;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .root .anchor path{fill:#333333!important;stroke-width:0;stroke:#333333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .arrowheadPath{fill:#333333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgePath .path{stroke:#333333;stroke-width:2.0px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .flowchart-link{stroke:#333333;fill:none;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel{background-color:rgba(232,232,232, 0.8);text-align:center;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel p{background-color:rgba(232,232,232, 0.8);}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .edgeLabel rect{opacity:0.5;background-color:rgba(232,232,232, 0.8);fill:rgba(232,232,232, 0.8);}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .labelBkg{background-color:rgba(232, 232, 232, 0.5);}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster rect{fill:#ffffde;stroke:#aaaa33;stroke-width:1px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster text{fill:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .cluster span{color:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:12px;background:hsl(80, 100%, 96.2745098039%);border:1px solid #aaaa33;border-radius:2px;pointer-events:none;z-index:100;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 rect.text{fill:none;stroke-width:0;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape{background-color:rgba(232,232,232, 0.8);text-align:center;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape p,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape p{background-color:rgba(232,232,232, 0.8);padding:2px;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .icon-shape rect,#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .image-shape rect{opacity:0.5;background-color:rgba(232,232,232, 0.8);fill:rgba(232,232,232, 0.8);}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-abc7d51d-cc53-4058-b9d6-84e4a616af90 :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}Test Casesquery_new_agent.pyEvaluation DatasetRAGAS EvaluationFoundry EvaluationRAGAS ResultsFoundry ResultsReports / AnalysisQA Review / Bug Analysis

🔮 Future Architecture (EvalOps Vision)
flowchart TD    A[Test Cases] --> B[Agent Execution]    B --> C[Evaluation Dataset]    C --> D[RAGAS]    C --> E[DeepEval - Planned]    C --> F[Foundry Evaluation]    D --> G[Metrics]    E --> G    F --> G    G --> H[Azure Monitor - Planned]    G --> I[Power BI Dashboard - Planned]    G --> J[Release Gates - Planned]Show more lines#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f {font-family:"trebuchet ms", verdana, arial, sans-seriffont-size:16px;fill:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-animation-slow {stroke-dashoffset:900animation-duration:50s;animation-timing-function:linear;animation-delay:0s;animation-iteration-count:infinite;animation-direction:normal;animation-fill-mode:none;animation-play-state:running;animation-name:dash;animation-timeline:auto;animation-range-start:normal;animation-range-end:normal;stroke-linecap:round;stroke-dasharray:9, 5;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-animation-fast {stroke-dashoffset:900animation-duration:20s;animation-timing-function:linear;animation-delay:0s;animation-iteration-count:infinite;animation-direction:normal;animation-fill-mode:none;animation-play-state:running;animation-name:dash;animation-timeline:auto;animation-range-start:normal;animation-range-end:normal;stroke-linecap:round;stroke-dasharray:9, 5;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .error-icon {fill:rgb(85, 34, 34)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .error-text {fill:rgb(85, 34, 34)stroke:rgb(85, 34, 34);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-normal {stroke-width:1px}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-thick {stroke-width:3.5px}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-solid {stroke-dasharray:0}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-invisible {stroke-width:0fill:none;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-dashed {stroke-dasharray:3}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-dotted {stroke-dasharray:2}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .marker {fill:rgb(51, 51, 51)stroke:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .marker.cross {stroke:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f svg {font-family:"trebuchet ms", verdana, arial, sans-seriffont-size:16px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f p {margin-top:0pxmargin-right:0px;margin-bottom:0px;margin-left:0px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label {font-family:"trebuchet ms", verdana, arial, sans-serifcolor:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label text {fill:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label span {color:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label span p {background-color:transparent}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label text, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f span {fill:rgb(51, 51, 51)color:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node rect, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node circle, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node ellipse, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node polygon, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node path {fill:rgb(236, 236, 255)stroke:rgb(147, 112, 219);stroke-width:1px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .rough-node .label text, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label text, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape .label, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape .label {text-anchor:middle}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .katex path {fill:rgb(0, 0, 0)stroke:rgb(0, 0, 0);stroke-width:1px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .rough-node .label, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape .label, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape .label {text-align:center}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node.clickable {cursor:pointer}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .root .anchor path {stroke-width:0stroke:rgb(51, 51, 51);fill:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .arrowheadPath {fill:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgePath .path {stroke:rgb(51, 51, 51)stroke-width:2px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .flowchart-link {stroke:rgb(51, 51, 51)fill:none;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel {background-color:rgba(232, 232, 232, 0.8)text-align:center;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel p {background-color:rgba(232, 232, 232, 0.8)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel rect {opacity:0.5background-color:rgba(232, 232, 232, 0.8);fill:rgba(232, 232, 232, 0.8);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .labelBkg {background-color:rgba(232, 232, 232, 0.5)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster rect {fill:rgb(255, 255, 222)stroke:rgb(170, 170, 51);stroke-width:1px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster text {fill:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster span {color:rgb(51, 51, 51)}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f div.mermaidTooltip {position:absolutetext-align:center;max-width:200px;padding-top:2px;padding-right:2px;padding-bottom:2px;padding-left:2px;font-family:"trebuchet ms", verdana, arial, sans-serif;font-size:12px;background-image:initial;background-position-x:initial;background-position-y:initial;background-size:initial;background-repeat:initial;background-attachment:initial;background-origin:initial;background-clip:initial;background-color:rgb(249, 255, 236);border-top-width:1px;border-right-width:1px;border-bottom-width:1px;border-left-width:1px;border-top-style:solid;border-right-style:solid;border-bottom-style:solid;border-left-style:solid;border-top-color:rgb(170, 170, 51);border-right-color:rgb(170, 170, 51);border-bottom-color:rgb(170, 170, 51);border-left-color:rgb(170, 170, 51);border-image-source:initial;border-image-slice:initial;border-image-width:initial;border-image-outset:initial;border-image-repeat:initial;border-top-left-radius:2px;border-top-right-radius:2px;border-bottom-right-radius:2px;border-bottom-left-radius:2px;pointer-events:none;z-index:100;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .flowchartTitleText {text-anchor:middlefont-size:18px;fill:rgb(51, 51, 51);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f rect.text {fill:nonestroke-width:0;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape {background-color:rgba(232, 232, 232, 0.8)text-align:center;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape p, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape p {background-color:rgba(232, 232, 232, 0.8)padding-top:2px;padding-right:2px;padding-bottom:2px;padding-left:2px;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape rect, #mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape rect {opacity:0.5background-color:rgba(232, 232, 232, 0.8);fill:rgba(232, 232, 232, 0.8);}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label-icon {display:inline-blockheight:1em;overflow-x:visible;overflow-y:visible;vertical-align:-0.125em;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label-icon path {fill:currentcolorstroke:revert;stroke-width:revert;}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f :root {--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif}
#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .error-icon{fill:#552222;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .error-text{fill:#552222;stroke:#552222;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-normal{stroke-width:1px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-thick{stroke-width:3.5px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-solid{stroke-dasharray:0;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .marker{fill:#333333;stroke:#333333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .marker.cross{stroke:#333333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f svg{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f p{margin:0;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label{font-family:"trebuchet ms",verdana,arial,sans-serif;color:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label text{fill:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label span{color:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster-label span p{background-color:transparent;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label text,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f span{fill:#333;color:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node rect,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node circle,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node ellipse,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node polygon,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node path{fill:#ECECFF;stroke:#9370DB;stroke-width:1px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .rough-node .label text,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label text,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape .label,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape .label{text-anchor:middle;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .rough-node .label,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape .label,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape .label{text-align:center;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node.clickable{cursor:pointer;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .root .anchor path{fill:#333333!important;stroke-width:0;stroke:#333333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .arrowheadPath{fill:#333333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgePath .path{stroke:#333333;stroke-width:2.0px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .flowchart-link{stroke:#333333;fill:none;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel{background-color:rgba(232,232,232, 0.8);text-align:center;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel p{background-color:rgba(232,232,232, 0.8);}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .edgeLabel rect{opacity:0.5;background-color:rgba(232,232,232, 0.8);fill:rgba(232,232,232, 0.8);}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .labelBkg{background-color:rgba(232, 232, 232, 0.5);}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster rect{fill:#ffffde;stroke:#aaaa33;stroke-width:1px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster text{fill:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .cluster span{color:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:12px;background:hsl(80, 100%, 96.2745098039%);border:1px solid #aaaa33;border-radius:2px;pointer-events:none;z-index:100;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#333;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f rect.text{fill:none;stroke-width:0;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape{background-color:rgba(232,232,232, 0.8);text-align:center;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape p,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape p{background-color:rgba(232,232,232, 0.8);padding:2px;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .icon-shape rect,#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .image-shape rect{opacity:0.5;background-color:rgba(232,232,232, 0.8);fill:rgba(232,232,232, 0.8);}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-da926e45-a864-4414-b58e-4d86d8a6878f :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}Test CasesAgent ExecutionEvaluation DatasetRAGASDeepEval - PlannedFoundry EvaluationMetricsAzure Monitor - PlannedPower BI Dashboard -PlannedRelease Gates - Planned

📂 Project Structure
playready-qa-automation/
│
├── scripts/              
├── tests/                
├── data/                 
├── ragas_layer/          
├── foundry_layer/        
├── audit/                
│
├── azure-pipelines.yml   
├── requirements.txt      
├── .gitignore            
└── README.md


🚀 Setup & Run
1. Setup
Shellpython -m venv .venv.venv\Scripts\activatepip install -r requirements.txtShow more lines

2. Azure Login
Shellaz loginShow more lines

3. Run Agent
Shellpython scripts/query_new_agent.pyShow more lines

4. Evaluate
Shellpython scripts/run_ragas_bridge.pyShow more lines

5. Run Tests
Shellpytest -vShow more lines

⚠️ Current Limitations

DeepEval not fully integrated
No centralized dashboard
Observability not yet implemented
Some analysis is manual


🔥 Roadmap

DeepEval integration
Power BI dashboards
Azure Monitor logging
Automated regression detection
Full EvalOps pipeline


🎯 Why This Project Matters
This framework enables:

repeatable QA
metric-driven evaluation
scalable testing
clean enterprise workflows


👨‍💻 Author
Sushrut Nistane
QA Automation Engineer – GenAI / RAG Systems

---

# ✅ ✅ FINAL CHECK BEFORE PUSH

👉 After replacing:

```powershell
git add README.md
git commit -m "📘 Clean README with architecture diagram"
git push

