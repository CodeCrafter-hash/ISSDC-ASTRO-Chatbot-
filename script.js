const inputField = document.getElementById("user-input");
const typingIndicator = document.getElementById("typing-indicator");

inputField.addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  appendMessage("🧑‍💻 You", message);
  input.value = "";

  typingIndicator.style.display = "block"; // Show typing

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: message,
        session_id: "user_1"
      })
    });

    const data = await res.json();
    appendMessage("🤖 ASTRO", data.response);
  } catch (error) {
    appendMessage("🤖 ASTRO", `⚠️ Error: ${error.message}`);
  } finally {
    typingIndicator.style.display = "none"; // Hide typing
  }
}

function appendMessage(sender, text) {
  const chatBox = document.getElementById("chat-box");
  const msgDiv = document.createElement("div");
  msgDiv.className = "message";
  msgDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

 
