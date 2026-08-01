import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod


class OutputFormatter(ABC):
    @abstractmethod
    def format(self, data):
        pass


class JSONFormatter(OutputFormatter):
    def format(self, data):
        return json.dumps(data, default=str, indent=2, ensure_ascii=False)


class XMLFormatter(OutputFormatter):
    def format(self, data):
        root = ET.Element('results')

        for key, value in data.items():
            section = ET.SubElement(root, key)

            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                for item in value:
                    row = ET.SubElement(section, 'row')
                    for k, v in item.items():
                        ET.SubElement(row, k).text = str(v)
            else:
                ET.SubElement(section, 'value').text = str(value)

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')