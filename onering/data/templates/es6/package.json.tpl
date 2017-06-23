{
  "name": "{{package.name}}",
  "version": "{{package.version}}",
  "description": "{{package.description.replace('\n', '')}}",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "files": [
    "index.js",
    "lib/"
  ],
  "dependencies": {
    {% for dep, version in package.current_platform.dependencies %}
        {% if loop.index0 > 0%},{% endif %}"{{ dep }}" : "{{ version }}"
    {% endfor %}
  },
  "author": "sri.panyam@gmail.com",
  "license": "ISC"
}
