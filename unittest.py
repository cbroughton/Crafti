# -*- coding: cp1252 -*-
import unittest
import packets

class TestPacketParsing(unittest.TestCase):

    def test_chat_color(self):
        packet = "\x00\x15<\xc2\xa7fMrZunz\xc2\xa7f> Alrite"
        parsed = packets.packets[3].parse(packet)
        self.assertEqual(parsed.message, u"<§fMrZunz§f> Alrite")

if __name__ == "__main__":
    unittest.main()
