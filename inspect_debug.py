import os

filename = "debug_google_0_results.html"
if os.path.exists(filename):
    size = os.path.getsize(filename)
    print(f"Size: {size}")
    
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        print(f"Preview: {content[:500]}")
        
        if "Google" in content:
            print("Contains 'Google'")
        else:
            print("Does NOT contain 'Google'")
            
        if "captcha" in content.lower():
            print("Contains 'captcha'")
            
        if "class=\"g\"" in content:
            print("Contains class='g'")
            
        if "<html" in content.lower():
             print("Contains <html> tag")

        keywords = ["Setuju", "Agree", "Before you continue", "unusual traffic", "robot", "consent", "form action", "recaptcha", "class=\"yKMVIe\""]
        for kw in keywords:
            if kw.lower() in content.lower():
                print(f"Found keyword: '{kw}'")
                
        # Check for any input fields which might suggest a form/captcha
        if "<input" in content:
            print("Found <input> tag")
else:
    print("File not found")
