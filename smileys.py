smileys = {
	':|': 'ambivalent',
	'B-)': 'cool',
	':(': 'frown',
	':O': 'gasp',
	':D': 'laugh',
	']-)': 'naughty',
	':)': 'smile',
	';)': 'wink',
	':P': 'yuck'
}
		
def make_smile(text):
	for key in smileys:
		text = text.replace(key, '<img class="smile" src="/static/smileys/' + smileys[key] + '.png" />')
	return text