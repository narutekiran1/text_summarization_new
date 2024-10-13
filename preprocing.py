import google.generativeai as genai   
GOOGLE_API_KEY='AIzaSyB2g451h6la4HEC8RjHBMYOSo9cqpaB7d0'   
genai.configure(api_key=GOOGLE_API_KEY) 
model = genai.GenerativeModel('gemini-pro')
def get(news):   
    response = model.generate_content(["your expert in summerizaing the steance in 1 or 2 lines but make sure that reading that you lines we should unberstnad whole sentace  and please dont add any new word only give the para which is already in news please i request dont give any word or line of setnace which in not in given news    sentace:"+news], stream=True) 
    response.resolve()   
    return response.text