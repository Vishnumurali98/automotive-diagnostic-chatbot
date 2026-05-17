function toggleChat() {

    const widget = document.getElementById("chat-widget");
    const body = document.body;

    // CHECK CURRENT VISIBILITY
    const isVisible = window.getComputedStyle(widget).display !== "none";

    // OPEN CHAT
    if (!isVisible) {

        widget.style.display = "flex";

        setTimeout(() => {
            widget.classList.add("chat-visible");
        }, 10);

        body.classList.add("chat-open");

        // Welcome message only once
        const chat = document.getElementById("chat-messages");

        if (chat.childElementCount === 0) {

            addMessage(
                "Hi 👋 I’m your Automotive AI Assistant.\n\n" +
                "You can:\n" +
                "🔧 Click 'Diagnose' to identify a problem\n" +
                "📅 Click 'Service' to book a service\n" +
                "🚗 Click 'Help' to learn how it works\n\n" +
                "Or type your issue below.",
                "bot"
            );
        }

    }

    // CLOSE CHAT
    else {

        widget.classList.remove("chat-visible");

        body.classList.remove("chat-open");

        setTimeout(() => {
            widget.style.display = "none";
        }, 300);
    }
}

function handleKey(e) {
    if (e.key === "Enter") sendMessage();
}

function addMessage(text, sender) {
    const chat = document.getElementById("chat-messages");

    const msg = document.createElement("div");
    msg.classList.add("message", sender);
    msg.innerText = text;

    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

function showTyping() {
    const chat = document.getElementById("chat-messages");

    const typing = document.createElement("div");
    typing.classList.add("message", "bot");
    typing.id = "typing";

    typing.innerHTML = `
        <div style="font-size:13px; opacity:0.8; margin-bottom:5px;">
            🔍 Analyzing your issue...
        </div>
        <div class="typing">
            <span></span><span></span><span></span>
        </div>
    `;

    chat.appendChild(typing);
    chat.scrollTop = chat.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById("typing");
    if (typing) typing.remove();
}

async function sendMessage() {

    const input = document.getElementById("user-input");
    const text = input.value.trim();

    if (!text) return;

    addMessage(text, "user");
    input.value = "";

    showTyping();

    const response = await fetch("/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    });

    const data = await response.json();

    removeTyping();
let label = "";

if (data.source === "rag_gemini") {
    label = "🔍 AI Diagnosis";
}
else if (data.source === "knowledge_base") {
    label = "📚 Quick Answer";
}
else if (data.source === "service_flow") {
    label = "📅 Service Assistant";
}
else if (data.source === "cache") {
    label = " Cached Response";
}

addMessage(data.reply + (label ? "\n\n" + label : ""), "bot");
}

function handleQuickAction(type) {

    if (type === "diagnose") {

        fetch("/set_mode", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({mode: "diagnose"})
        });

        addMessage(
            "🔧 Diagnosis Mode Activated\n\n" +
            "Describe your issue (e.g., engine overheating, brake noise).",
            "bot"
        );
    }

    else if (type === "service") {
     fetch("/set_mode", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({mode: "service"})
    });
        addMessage(
            "📅 Service Booking\n\n" +
            "Please provide your preferred service date.",
            "bot"
        );
    }

    else if (type === "help") {
        addMessage(
            "🚗 Help Guide\n\n" +
            "1. Click Diagnose → to find vehicle issues\n" +
            "2. Click Service → to book service\n" +
            "3. Or type your issue directly",
            "bot"
        );
    }
}