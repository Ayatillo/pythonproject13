
import { createBoard, playMove } from "./connect4.js";

const PLAYER1 = "red";
const PLAYER2 = "yellow";

let timer;
let timeLeft = 20;

function initGame(websocket) {
  websocket.addEventListener("open", () => {
    const params = new URLSearchParams(window.location.search);
    let event = { type: "init" };
    if (params.has("join")) {
      event.join = params.get("join");
    } else if (params.has("watch")) {
      event.watch = params.get("watch");
    } else {
      // First player starts a new game.
    }
    websocket.send(JSON.stringify(event));
  });
}

function showMessage(message) {
  window.setTimeout(() => window.alert(message), 50);
}

function receiveMoves(board, websocket) {
  websocket.addEventListener("message", ({ data }) => {
    const event = JSON.parse(data);
    switch (event.type) {
      case "init":
        document.querySelector(".join").href = "?join=" + event.join;
        document.querySelector(".watch").href = "?watch=" + event.watch;
        break;
      case "play":
        playMove(board, event.player, event.column, event.row);
        resetTimer();
        break;
      case "win":
        showMessage(`Player ${event.player} wins!`);
        clearInterval(timer);
        websocket.close(1000);
        break;
      case "error":
        showMessage(event.message);
        break;
      default:
        throw new Error(`Unsupported event type: ${event.type}.`);
    }
  });
}

function sendMoves(board, websocket) {
  const params = new URLSearchParams(window.location.search);
  if (params.has("watch")) {
    return;
  }

  board.addEventListener("click", ({ target }) => {
    clearTimeout(timer);
    const column = target.dataset.column;
    if (column === undefined) {
      return;
    }
    const event = {
      type: "play",
      column: parseInt(column, 10),
    };
    websocket.send(JSON.stringify(event));
    resetTimer();
  });

  startTimer(websocket);
}

function startTimer(websocket) {
  timeLeft = 20;
  timer = setInterval(() => {
    timeLeft--;
    document.getElementById("timer-display").textContent = timeLeft;
    if (timeLeft <= 0) {
      const params = new URLSearchParams(window.location.search);
      const currentPlayer = params.has("join") ? PLAYER2 : PLAYER1;
      showMessage(`Player ${currentPlayer} wins! The other player took too long.`);
      clearInterval(timer);
      const closeEvent = {
        type: "close",
        player: currentPlayer,
      };
      websocket.send(JSON.stringify(closeEvent));
      websocket.close(1000);
    }
  }, 1000);
}

function resetTimer() {
  clearInterval(timer);
  startTimer();
  const params = new URLSearchParams(window.location.search);
  const currentPlayer = params.has("join") ? PLAYER2 : PLAYER1;
  const closeEvent = {
    type: "close",
    player: currentPlayer,
  };
  websocket.send(JSON.stringify(closeEvent));
}

window.addEventListener("DOMContentLoaded", () => {
  const board = document.querySelector(".board");
  createBoard(board);
  const websocket = new WebSocket("ws://localhost:8001/");
  initGame(websocket);
  receiveMoves(board, websocket);
  sendMoves(board, websocket);
});