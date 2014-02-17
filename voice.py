import httplib
import urllib
import urllib2

url = "http://translate.google.com/translate_tts?tl=pt&q=%s" % "Voc%C3%AA+est%C3%A1+ouvindo+a+r%C3%A1dio+LSD"
request = urllib2.Request(url)
request.add_header('User-agent', 'Mozilla/5.0') 
opener = urllib2.build_opener()

f = open("data.mp3", "wb")
f.write(opener.open(request).read())
f.close()