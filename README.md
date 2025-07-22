
# ✈️ Travel Query Parser

This is a simple yet powerful Python-based Travel Query Parser that extracts useful travel information (like source city and date) from natural language input. It's designed for use in a travel chatbot or any ticket booking automation system.

---

## 🧠 Features

- ✅ Extracts **source city** from user input using fuzzy matching and spell correction
- ✅ Extracts **date** from natural phrases like "tomorrow", "8th August", or "next Friday"
- ✅ Uses **spaCy NLP**, **RapidFuzz** for fuzzy matching, **Autocorrect** for spelling correction, and **Parsedatetime** for interpreting human language dates

---

## 🏗️ Project Structure

```
├── extract_parameters.py       # Main script to run the parser
├── requirements.txt            # Dependencies
└── README.md                   # Project documentation
```

---

## 📦 Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/travel-query-parser.git
cd travel-query-parser
```

2. **Create a virtual environment** (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Download spaCy model**

```bash
python -m spacy download en_core_web_sm
```

---

## 🚀 Usage

Run the parser and enter your travel query:

```bash
python extract_parameters.py
```

### Example Queries:

```
> I want to go from Lahore to Karachi tomorrow
{'source': 'Lahore', 'destination': 'Karachi', 'date': '2025-07-23'}

> Book a ticket from Islambad to Khi on 8th of Aug
{'source': 'Islamabad', 'destination': 'Karachi', 'date': '2025-08-08'}
```

---

## 🧪 Technologies Used

- [spaCy](https://spacy.io/) – NLP pipeline for entity parsing
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) – Fast fuzzy string matching
- [Autocorrect](https://github.com/phatpiglet/autocorrect) – Automatic spelling correction
- [Parsedatetime](https://github.com/bear/parsedatetime) – Natural language date parsing

---

## 📝 License

MIT License. Feel free to use, fork, and improve!

---

## 👨‍💻 Author

Built with ❤️ by [Your Name]  
Need help? Open an issue or email me at you@example.com
