import requests
import json

BASE_URL = "http://localhost/api"

def search():
    topic = input("\n🔍 Enter topic to search (e.g., distributed): ").strip()
    try:
        r = requests.get(f"{BASE_URL}/search", params={"topic": topic}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return

    data = r.json()
    items = data.get("items", {})

    # handle both list and dict
    if isinstance(items, dict):
        items = [{"title": t, "id": i} for t, i in items.items()]

    if not items:
        print("⚠  No books found for that topic.")
        return

    print("\n📚 Books found:")
    for item in items:
        print(f"  #{item['id']:>2}  {item['title']}")
    print()

def info():
    try:
        book_id = int(input("\nℹ  Enter book ID: ").strip())
    except ValueError:
        print("⚠  Invalid ID.")
        return

    try:
        r = requests.get(f"{BASE_URL}/info/{book_id}", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Error fetching info: {e}")
        return

    data = r.json()
    print("\n📖 Book Info:")
    print(json.dumps(data, indent=2))
    print()

def purchase():
    try:
        book_id = int(input("\n💳 Enter book ID to purchase: ").strip())
    except ValueError:
        print("⚠  Invalid ID.")
        return

    try:
        r = requests.post(f"{BASE_URL}/buy/{book_id}", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Error completing purchase: {e}")
        return

    data = r.json()
    if data.get("ok"):
        print(f"✅ Bought book #{book_id} successfully!")
    else:
        print("❌ Purchase failed:", data)
    print()

def main():
    print("📦 Welcome to Bazar.com CLI")
    print("Simple client for Catalog & Order microservices.\n")

    while True:
        print("Select an option:")
        print("  1️⃣  Search for books by topic")
        print("  2️⃣  Get book info")
        print("  3️⃣  Purchase a book")
        print("  4️⃣  Exit")
        choice = input("👉 Enter choice: ").strip()

        if choice == "1":
            search()
        elif choice == "2":
            info()
        elif choice == "3":
            purchase()
        elif choice == "4":
            print("\n👋 Exiting... Have a nice day!\n")
            break
        else:
            print("⚠  Invalid option, please try again.\n")

if __name__ == "__main__":
    main()