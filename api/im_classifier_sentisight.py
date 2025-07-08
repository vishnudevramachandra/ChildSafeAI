import requests
import json
import ast

def detect_nsfw_uri(image_uri, thres):
	"""Detects unsafe imagees on the Web."""

	token = "qr8psfemsn68qud85sb7dj4ufg"
	model = "NSFW-classification"  # "General-classification", "Places-classification", "NSFW-classification" or "Object-detection"
	# image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6BjYozZloyQtA6_M_Qxs7KhyV2caxRdCYug&s"

	payload = json.dumps({
		"url": image_uri
	})

	headers = {"X-Auth-token": token, "Content-Type": "application/json"}

	r = requests.post('https://platform.sentisight.ai/api/pm-predict/{}/'.format(model), headers=headers, data=payload)

	if r.status_code == 200:
		return (1 if ast.literal_eval(r.text)[0]['score'] > thres else 0)
	else:
		print('Error occured with REST API.')
		print('Status code: {}'.format(r.status_code))
		print('Error message: ' + r.text)
		return (0)


if __name__ == '__main__':
	detect_nsfw_uri('https://storage.googleapis.com/api4ai-static/samples/general-cls-2.jpg', 50)
	detect_nsfw_uri("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6BjYozZloyQtA6_M_Qxs7KhyV2caxRdCYug&s", 50)	