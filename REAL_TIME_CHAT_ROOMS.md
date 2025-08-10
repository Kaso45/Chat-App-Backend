# Real-Time Chat Room Updates

This implementation provides real-time updates for chat room creation, allowing participants to see new chat rooms immediately without refreshing the page.

## How It Works

### Backend Implementation

1. **WebSocket Event Type**: Added `NEW_CHAT_ROOM` to the payload types
2. **Broadcasting**: When a new chat room is created, all participants receive a WebSocket notification
3. **Cache Updates**: The new chat room is automatically cached for all participants

### WebSocket Message Format

When a new chat room is created, participants receive this WebSocket message:

```json
{
  "type": "new_chat_room",
  "chat_room": {
    "chat_id": "507f1f77bcf86cd799439011",
    "chat_name": "My New Chat",
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

## Frontend Implementation

### JavaScript/TypeScript Example

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws");

// Handle incoming messages
ws.onmessage = function (event) {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case "new_chat_room":
      // Add the new chat room to the UI
      addNewChatRoom(data.chat_room);
      break;

    case "personal_message":
      // Handle personal message
      handlePersonalMessage(data.data);
      break;

    case "group_message":
      // Handle group message
      handleGroupMessage(data.chat_id, data.data);
      break;
  }
};

// Function to add new chat room to UI
function addNewChatRoom(chatRoom) {
  const chatList = document.getElementById("chat-list");

  const chatElement = document.createElement("div");
  chatElement.className = "chat-item";
  chatElement.innerHTML = `
    <div class="chat-name">${chatRoom.chat_name || "Unnamed Chat"}</div>
    <div class="chat-time">${new Date(
      chatRoom.last_updated
    ).toLocaleString()}</div>
  `;

  // Add click handler to open chat
  chatElement.onclick = () => openChat(chatRoom.chat_id);

  // Insert at the top of the list (newest first)
  chatList.insertBefore(chatElement, chatList.firstChild);

  // Optional: Show notification
  showNotification(`New chat room: ${chatRoom.chat_name || "Unnamed Chat"}`);
}

function showNotification(message) {
  // Implementation depends on your UI framework
  // Example with browser notifications:
  if (Notification.permission === "granted") {
    new Notification("New Chat Room", { body: message });
  }
}
```

### React Example

```jsx
import { useEffect, useState } from "react";

function ChatList() {
  const [chatRooms, setChatRooms] = useState([]);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket("ws://localhost:8000/ws");

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "new_chat_room") {
        // Add new chat room to the beginning of the list
        setChatRooms((prev) => [data.chat_room, ...prev]);

        // Show notification
        if (Notification.permission === "granted") {
          new Notification("New Chat Room", {
            body: data.chat_room.chat_name || "Unnamed Chat",
          });
        }
      }
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  return (
    <div className="chat-list">
      {chatRooms.map((chat) => (
        <div key={chat.chat_id} className="chat-item">
          <div className="chat-name">{chat.chat_name || "Unnamed Chat"}</div>
          <div className="chat-time">
            {new Date(chat.last_updated).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### Vue.js Example

```vue
<template>
  <div class="chat-list">
    <div
      v-for="chat in chatRooms"
      :key="chat.chat_id"
      class="chat-item"
      @click="openChat(chat.chat_id)"
    >
      <div class="chat-name">{{ chat.chat_name || "Unnamed Chat" }}</div>
      <div class="chat-time">{{ formatTime(chat.last_updated) }}</div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      chatRooms: [],
      ws: null,
    };
  },

  mounted() {
    this.connectWebSocket();
  },

  beforeUnmount() {
    if (this.ws) {
      this.ws.close();
    }
  },

  methods: {
    connectWebSocket() {
      this.ws = new WebSocket("ws://localhost:8000/ws");

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "new_chat_room") {
          // Add new chat room to the beginning
          this.chatRooms.unshift(data.chat_room);

          // Show notification
          this.showNotification(data.chat_room.chat_name || "Unnamed Chat");
        }
      };
    },

    showNotification(message) {
      if (Notification.permission === "granted") {
        new Notification("New Chat Room", { body: message });
      }
    },

    formatTime(timestamp) {
      return new Date(timestamp).toLocaleString();
    },

    openChat(chatId) {
      // Navigate to chat
      this.$router.push(`/chat/${chatId}`);
    },
  },
};
</script>
```

## Testing

1. **Create a chat room** using the API endpoints:

   - `POST /api/chat/create/personal`
   - `POST /api/chat/create/group`

2. **Connect multiple users** to the WebSocket endpoint:

   - `GET /ws`

3. **Create a new chat room** and verify that all participants receive the real-time notification

## Benefits

- **Immediate Updates**: No need to refresh or poll for new chat rooms
- **Efficient**: Uses WebSocket for real-time communication
- **Scalable**: Works with the existing caching system
- **Consistent**: Maintains the same data structure as the REST API

## Notes

- The WebSocket connection requires authentication (same as the REST API)
- Chat rooms are automatically cached for all participants
- The implementation handles both personal and group chats
- Error handling is included for WebSocket connection issues
