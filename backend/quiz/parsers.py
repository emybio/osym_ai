"""
Robust JSON Parser for handling encoding issues
Fixes UTF-8 codec errors on Windows
"""
import json
import io
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError


class RobustJSONParser(JSONParser):
    """
    Enhanced JSON parser that handles encoding issues gracefully
    """

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream with robust error handling
        """
        try:
            # Read the raw bytes
            raw_data = stream.read()

            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

            for encoding in encodings:
                try:
                    # Decode the bytes
                    text_data = raw_data.decode(encoding)
                    # Parse as JSON
                    return json.loads(text_data)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

            # If all encodings fail, try with error handling
            try:
                text_data = raw_data.decode('utf-8', errors='replace')
                return json.loads(text_data)
            except json.JSONDecodeError:
                pass

            # Last resort: try to parse as-is
            text_data = raw_data.decode('utf-8', errors='ignore')
            try:
                return json.loads(text_data)
            except json.JSONDecodeError as e:
                raise ParseError(f'JSON parse error - {str(e)}')

        except Exception as e:
            raise ParseError(f'Parse error - {str(e)}')