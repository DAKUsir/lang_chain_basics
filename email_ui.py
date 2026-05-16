"""
Automated Email Sender - Tkinter UI
- Fill in recipient, subject, and instructions
- Gemini AI composes the email body
- Edit the body before sending
- Send via Gmail SMTP
"""

import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# ── LangChain setup ───────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional email writer. "
        "Write a clear, concise, and polite email based on the user's instructions. "
        "Return ONLY the email body — no subject line, no greetings header, just the body text.",
    ),
    ("human", "{instructions}"),
])
email_chain = prompt | llm


def compose_email(instructions: str) -> str:
    response = email_chain.invoke({"instructions": instructions})
    return response.content.strip()


def send_email(to: str, subject: str, body: str):
    msg = MIMEMultipart("alternative")
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to, msg.as_string())


# ── Tkinter UI ────────────────────────────────────────────────────────────────

class EmailApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Email Sender")
        self.resizable(True, True)
        self.configure(bg="#f0f4f8")
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        PAD = {"padx": 12, "pady": 6}

        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#4a90d9", pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="✉  AI Email Sender",
            font=("Helvetica", 18, "bold"),
            bg="#4a90d9", fg="white"
        ).pack()

        # ── Main frame ────────────────────────────────────────────────────────
        main = tk.Frame(self, bg="#f0f4f8", padx=20, pady=10)
        main.pack(fill="both", expand=True)

        # To
        tk.Label(main, text="To:", bg="#f0f4f8", font=("Helvetica", 11, "bold")).grid(
            row=0, column=0, sticky="w", **PAD)
        self.to_var = tk.StringVar()
        tk.Entry(main, textvariable=self.to_var, width=55, font=("Helvetica", 11)).grid(
            row=0, column=1, sticky="ew", **PAD)

        # Subject
        tk.Label(main, text="Subject:", bg="#f0f4f8", font=("Helvetica", 11, "bold")).grid(
            row=1, column=0, sticky="w", **PAD)
        self.subject_var = tk.StringVar()
        tk.Entry(main, textvariable=self.subject_var, width=55, font=("Helvetica", 11)).grid(
            row=1, column=1, sticky="ew", **PAD)

        # Instructions
        tk.Label(main, text="Instructions\n(for AI):", bg="#f0f4f8",
                 font=("Helvetica", 11, "bold"), justify="left").grid(
            row=2, column=0, sticky="nw", **PAD)
        self.instructions_box = scrolledtext.ScrolledText(
            main, width=55, height=5, font=("Helvetica", 11), wrap="word",
            relief="solid", bd=1
        )
        self.instructions_box.grid(row=2, column=1, sticky="ew", **PAD)

        # Generate button
        self.gen_btn = tk.Button(
            main, text="🤖  Generate Email Body",
            command=self._on_generate,
            bg="#4a90d9", fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", padx=10, pady=6, cursor="hand2"
        )
        self.gen_btn.grid(row=3, column=1, sticky="w", **PAD)

        # Status label
        self.status_var = tk.StringVar(value="")
        tk.Label(main, textvariable=self.status_var, bg="#f0f4f8",
                 fg="#888", font=("Helvetica", 10, "italic")).grid(
            row=3, column=1, sticky="e", **PAD)

        # Separator
        ttk.Separator(main, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=8)

        # Email body (editable)
        tk.Label(main, text="Email Body\n(editable):", bg="#f0f4f8",
                 font=("Helvetica", 11, "bold"), justify="left").grid(
            row=5, column=0, sticky="nw", **PAD)
        self.body_box = scrolledtext.ScrolledText(
            main, width=55, height=12, font=("Helvetica", 11), wrap="word",
            relief="solid", bd=1
        )
        self.body_box.grid(row=5, column=1, sticky="nsew", **PAD)

        # Buttons row
        btn_frame = tk.Frame(main, bg="#f0f4f8")
        btn_frame.grid(row=6, column=1, sticky="e", **PAD)

        tk.Button(
            btn_frame, text="🗑  Clear",
            command=self._clear_all,
            bg="#e0e0e0", fg="#333",
            font=("Helvetica", 10), relief="flat", padx=8, pady=5, cursor="hand2"
        ).pack(side="left", padx=4)

        self.send_btn = tk.Button(
            btn_frame, text="📤  Send Email",
            command=self._on_send,
            bg="#27ae60", fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", padx=12, pady=6, cursor="hand2"
        )
        self.send_btn.pack(side="left", padx=4)

        main.columnconfigure(1, weight=1)
        main.rowconfigure(5, weight=1)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _on_generate(self):
        instructions = self.instructions_box.get("1.0", "end").strip()
        if not instructions:
            messagebox.showwarning("Missing", "Please enter instructions for the AI.")
            return
        self.gen_btn.config(state="disabled")
        self.status_var.set("⏳ Generating...")
        threading.Thread(target=self._generate_thread, args=(instructions,), daemon=True).start()

    def _generate_thread(self, instructions):
        try:
            body = compose_email(instructions)
            self.after(0, self._set_body, body)
        except Exception as e:
            self.after(0, messagebox.showerror, "Generation Error", str(e))
        finally:
            self.after(0, self.gen_btn.config, {"state": "normal"})
            self.after(0, self.status_var.set, "")

    def _set_body(self, body: str):
        self.body_box.delete("1.0", "end")
        self.body_box.insert("1.0", body)
        self.status_var.set("✅ Body generated — edit if needed")

    def _on_send(self):
        to      = self.to_var.get().strip()
        subject = self.subject_var.get().strip()
        body    = self.body_box.get("1.0", "end").strip()

        if not to:
            messagebox.showwarning("Missing", "Please enter a recipient email.")
            return
        if not subject:
            messagebox.showwarning("Missing", "Please enter a subject.")
            return
        if not body:
            messagebox.showwarning("Missing", "Email body is empty.")
            return
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            messagebox.showerror(
                "Credentials Missing",
                "Set EMAIL_SENDER and EMAIL_PASSWORD in your .env file."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Send",
            f"Send email to:\n{to}\n\nSubject: {subject}\n\nProceed?"
        )
        if not confirm:
            return

        self.send_btn.config(state="disabled")
        self.status_var.set("⏳ Sending...")
        threading.Thread(target=self._send_thread, args=(to, subject, body), daemon=True).start()

    def _send_thread(self, to, subject, body):
        try:
            send_email(to, subject, body)
            self.after(0, messagebox.showinfo, "Success", f"✅ Email sent to {to}")
            self.after(0, self.status_var.set, "✅ Sent!")
        except Exception as e:
            self.after(0, messagebox.showerror, "Send Error", str(e))
            self.after(0, self.status_var.set, "❌ Failed to send")
        finally:
            self.after(0, self.send_btn.config, {"state": "normal"})

    def _clear_all(self):
        self.to_var.set("")
        self.subject_var.set("")
        self.instructions_box.delete("1.0", "end")
        self.body_box.delete("1.0", "end")
        self.status_var.set("")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = EmailApp()
    app.mainloop()
