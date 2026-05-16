"""
Automated Email Sender
- Tkinter UI to fill recipient, subject, and prompt
- Gemini composes the email body from your prompt
- Edit the body before sending
- Sends via Gmail SMTP
"""

import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# ── Gemini setup ──────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional email writer. "
        "Write a clear, concise, and polite email body based on the user's instructions. "
        "Return ONLY the email body text — no subject line, no extra labels.",
    ),
    ("human", "{instructions}"),
])

chain = prompt_template | llm


def compose_email(instructions: str) -> str:
    """Ask Gemini to write the email body."""
    return chain.invoke({"instructions": instructions}).content.strip()


# ── Gmail SMTP sender ─────────────────────────────────────────────────────────
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
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Email Sender")
        self.configure(bg="#f0f4f8")
        self.resizable(True, True)
        self._build()

    def _build(self):
        P = dict(padx=12, pady=5)

        # Header
        tk.Frame(self, bg="#4a90d9", height=4).pack(fill="x")
        tk.Label(self, text="✉  AI Email Sender",
                 font=("Helvetica", 16, "bold"),
                 bg="#4a90d9", fg="white", pady=10).pack(fill="x")
        tk.Frame(self, bg="#4a90d9", height=4).pack(fill="x")

        form = tk.Frame(self, bg="#f0f4f8", padx=20, pady=12)
        form.pack(fill="both", expand=True)

        def label(row, text):
            tk.Label(form, text=text, bg="#f0f4f8",
                     font=("Helvetica", 10, "bold"), anchor="w").grid(
                row=row, column=0, sticky="nw", **P)

        # To
        label(0, "To:")
        self.to_var = tk.StringVar()
        tk.Entry(form, textvariable=self.to_var,
                 font=("Helvetica", 11), relief="solid", bd=1).grid(
            row=0, column=1, sticky="ew", **P)

        # Subject
        label(1, "Subject:")
        self.subject_var = tk.StringVar()
        tk.Entry(form, textvariable=self.subject_var,
                 font=("Helvetica", 11), relief="solid", bd=1).grid(
            row=1, column=1, sticky="ew", **P)

        # Prompt / Instructions
        label(2, "Prompt\n(tell AI what\nto write):")
        self.prompt_box = scrolledtext.ScrolledText(
            form, height=4, font=("Helvetica", 11),
            wrap="word", relief="solid", bd=1)
        self.prompt_box.grid(row=2, column=1, sticky="ew", **P)

        # Generate button + status
        gen_row = tk.Frame(form, bg="#f0f4f8")
        gen_row.grid(row=3, column=1, sticky="w", **P)

        self.gen_btn = tk.Button(
            gen_row, text="🤖  Generate with Gemini",
            command=self._generate,
            bg="#4a90d9", fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", padx=10, pady=5, cursor="hand2")
        self.gen_btn.pack(side="left")

        self.status = tk.StringVar()
        tk.Label(gen_row, textvariable=self.status,
                 bg="#f0f4f8", fg="#555",
                 font=("Helvetica", 10, "italic")).pack(side="left", padx=10)

        # Separator
        ttk.Separator(form, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=8)

        # Email body (editable)
        label(5, "Email Body\n(edit freely):")
        self.body_box = scrolledtext.ScrolledText(
            form, height=12, font=("Helvetica", 11),
            wrap="word", relief="solid", bd=1)
        self.body_box.grid(row=5, column=1, sticky="nsew", **P)

        # Bottom buttons
        btn_row = tk.Frame(form, bg="#f0f4f8")
        btn_row.grid(row=6, column=1, sticky="e", pady=10)

        tk.Button(btn_row, text="🗑  Clear",
                  command=self._clear,
                  bg="#ddd", fg="#333",
                  font=("Helvetica", 10),
                  relief="flat", padx=8, pady=5,
                  cursor="hand2").pack(side="left", padx=6)

        self.send_btn = tk.Button(
            btn_row, text="📤  Send Email",
            command=self._send,
            bg="#27ae60", fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", padx=12, pady=6,
            cursor="hand2")
        self.send_btn.pack(side="left")

        form.columnconfigure(1, weight=1)
        form.rowconfigure(5, weight=1)

    # ── Generate ──────────────────────────────────────────────────────────────
    def _generate(self):
        instructions = self.prompt_box.get("1.0", "end").strip()
        if not instructions:
            messagebox.showwarning("Empty Prompt", "Enter a prompt for the AI first.")
            return
        self.gen_btn.config(state="disabled")
        self.status.set("⏳ Generating...")
        threading.Thread(target=self._generate_worker,
                         args=(instructions,), daemon=True).start()

    def _generate_worker(self, instructions):
        try:
            body = compose_email(instructions)
            self.after(0, self._set_body, body)
        except Exception as e:
            self.after(0, messagebox.showerror, "Gemini Error", str(e))
            self.after(0, self.status.set, "❌ Generation failed")
        finally:
            self.after(0, self.gen_btn.config, {"state": "normal"})

    def _set_body(self, body):
        self.body_box.delete("1.0", "end")
        self.body_box.insert("1.0", body)
        self.status.set("✅ Done — edit the body if needed")

    # ── Send ──────────────────────────────────────────────────────────────────
    def _send(self):
        to      = self.to_var.get().strip()
        subject = self.subject_var.get().strip()
        body    = self.body_box.get("1.0", "end").strip()

        if not to:
            messagebox.showwarning("Missing", "Enter a recipient email address.")
            return
        if not subject:
            messagebox.showwarning("Missing", "Enter a subject.")
            return
        if not body:
            messagebox.showwarning("Missing", "Email body is empty. Generate or type one.")
            return
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            messagebox.showerror("Credentials Missing",
                                 "Set EMAIL_SENDER and EMAIL_PASSWORD in your .env file.")
            return

        if not messagebox.askyesno("Confirm", f"Send to:\n{to}\n\nSubject: {subject}"):
            return

        self.send_btn.config(state="disabled")
        self.status.set("⏳ Sending...")
        threading.Thread(target=self._send_worker,
                         args=(to, subject, body), daemon=True).start()

    def _send_worker(self, to, subject, body):
        try:
            send_email(to, subject, body)
            self.after(0, messagebox.showinfo, "Sent!", f"✅ Email sent to {to}")
            self.after(0, self.status.set, "✅ Email sent!")
        except smtplib.SMTPAuthenticationError:
            self.after(0, messagebox.showerror, "Auth Error",
                       "Gmail rejected the credentials.\n\n"
                       "Use a Gmail App Password (not your main password).\n"
                       "Generate one at: Google Account → Security → App Passwords")
            self.after(0, self.status.set, "❌ Auth failed")
        except Exception as e:
            self.after(0, messagebox.showerror, "Send Error", str(e))
            self.after(0, self.status.set, "❌ Failed")
        finally:
            self.after(0, self.send_btn.config, {"state": "normal"})

    # ── Clear ─────────────────────────────────────────────────────────────────
    def _clear(self):
        self.to_var.set("")
        self.subject_var.set("")
        self.prompt_box.delete("1.0", "end")
        self.body_box.delete("1.0", "end")
        self.status.set("")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
