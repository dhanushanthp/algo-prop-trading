from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from statistics import mean 
import math

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QLabel,
    QRadioButton,
    QMessageBox
)

from PyQt5.QtWidgets import QMessageBox

import MetaTrader5 as mt

class ScrollLabel(QScrollArea):
    """
    
    https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py#order_type
    https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py

    Args:
        QScrollArea (_type_): _description_

    Returns:
        _type_: _description_
    """
    # constructor
    def __init__(self, *args, **kwargs):
        QScrollArea.__init__(self, *args, **kwargs)

        # making widget resizable
        self.setWidgetResizable(True)

        # making qwidget object
        content = QWidget(self)
        self.setWidget(content)

        # vertical box layout
        lay = QVBoxLayout(content)

        # creating label
        self.label = QLabel(content)

        # making label multi-line
        self.label.setWordWrap(True)
        
        # adding label to the layout
        lay.addWidget(self.label)    

    # the setText method
    def setText(self, text):
        # setting text to the label
        self.label.setText(text)

    # getting text method
    def text(self):
        # getting text of the label
        get_text = self.label.text()

        # return the text
        return get_text
    
class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__(None, QtCore.Qt.WindowStaysOnTopHint)
        mt.initialize()
        
        # super(MyWindow, self).__init__()
        self.left_align = 10
        self.vertical_gap = 5  # Gap abouve the current element
        self.initUI()
        
        """
        ########################
        Login Credentials 
        #######################
        """
        
        # Value in USD
        self.risk = 50
        self.currencies = ["AUDNZD", "AUDJPY", "USDJPY", "USDCHF", "EURUSD", "XAUUSD"]
        
    def initUI(self):
        # Font Initiation
        header_font = QtGui.QFont()
        header_font.setBold(True)
        header_font.setPixelSize(20)

        button_font = QtGui.QFont()
        button_font.setBold(True)
        button_font.setPixelSize(20)

        label_font = QtGui.QFont()
        label_font.setBold(True)
        label_font.setPixelSize(18)
        
        text_input_font = QtGui.QFont()
        text_input_font.setBold(True)
        text_input_font.setPixelSize(22)

        ratio_font = QtGui.QFont()
        ratio_font.setPixelSize(16)

        vertical_align = 5
        
        self.btn_width = 160
        self.btn_height = 50
        self.left_margin = 15
        self.btn_gap = 200
        self.vert_gap = 60

        # Set the title and windows size
        self.setGeometry(20, 300, 380, 700)

        # Set application icon
        self.setWindowTitle("FTMO")      

        # Radio Button
        vertical_align += self.vertical_gap + 10
        self.radioButton1 = QRadioButton(self)
        self.radioButton1.move(self.left_margin, vertical_align)
        self.radioButton1.setText("US500")
        self.radioButton1.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton1.setFont(label_font)
        
        self.radioButton2 = QRadioButton(self)
        self.radioButton2.move(140, vertical_align)
        self.radioButton2.setText("UK100")
        self.radioButton2.setFont(label_font)
        self.radioButton2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton3 = QRadioButton(self)
        self.radioButton3.move(260, vertical_align)
        self.radioButton3.setText("HK50")
        self.radioButton3.setFont(label_font)
        self.radioButton3.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        
        vertical_align += self.vertical_gap + 40
        self.radioButton4 = QRadioButton(self)
        self.radioButton4.move(self.left_margin, vertical_align)
        self.radioButton4.setText("JP225")
        self.radioButton4.setFont(label_font)
        self.radioButton4.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton5 = QRadioButton(self)
        self.radioButton5.move(140, vertical_align)
        self.radioButton5.setText("AUS200")
        self.radioButton5.setFont(label_font)
        self.radioButton5.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton6 = QRadioButton(self)
        self.radioButton6.move(260, vertical_align)
        self.radioButton6.setText("US100")
        self.radioButton6.setFont(label_font)
        self.radioButton6.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        vertical_align += self.vertical_gap + 40
        self.radioButton7 = QRadioButton(self)
        self.radioButton7.move(self.left_margin, vertical_align)
        self.radioButton7.setText("AUDNZD")
        self.radioButton7.setFont(label_font)
        self.radioButton7.resize(140, 40)
        self.radioButton7.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton8 = QRadioButton(self)
        self.radioButton8.move(140, vertical_align)
        self.radioButton8.setText("USDJPY")
        self.radioButton8.setFont(label_font)
        self.radioButton8.resize(140, 40)
        self.radioButton8.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton9 = QRadioButton(self)
        self.radioButton9.move(260, vertical_align)
        self.radioButton9.setText("USDCHF")
        self.radioButton9.setFont(label_font)
        self.radioButton9.resize(140, 40)
        self.radioButton9.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        vertical_align += self.vertical_gap + 40
        self.radioButton10 = QRadioButton(self)
        self.radioButton10.move(self.left_margin, vertical_align)
        self.radioButton10.setText("AUDJPY")
        self.radioButton10.setFont(label_font)
        self.radioButton10.resize(140, 40)
        self.radioButton10.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton11 = QRadioButton(self)
        self.radioButton11.move(140, vertical_align)
        self.radioButton11.setText("XAUUSD")
        self.radioButton11.setFont(label_font)
        self.radioButton11.resize(140, 40)
        self.radioButton11.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.radioButton12 = QRadioButton(self)
        self.radioButton12.move(260, vertical_align)
        self.radioButton12.setText("EURUSD")
        self.radioButton12.setFont(label_font)
        self.radioButton12.resize(140, 40)
        self.radioButton12.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Set the initial state of the radio buttons (optional)
        # self.radioButton1.setChecked(True)
        # self.onRadioButtonToggled()

        # Connect a function to be called when a radio button is toggled
        self.radioButton1.toggled.connect(self.onRadioButtonToggled)
        self.radioButton2.toggled.connect(self.onRadioButtonToggled)
        self.radioButton3.toggled.connect(self.onRadioButtonToggled)
        self.radioButton4.toggled.connect(self.onRadioButtonToggled)
        self.radioButton5.toggled.connect(self.onRadioButtonToggled)
        self.radioButton6.toggled.connect(self.onRadioButtonToggled)
        self.radioButton7.toggled.connect(self.onRadioButtonToggled)
        self.radioButton8.toggled.connect(self.onRadioButtonToggled)
        self.radioButton9.toggled.connect(self.onRadioButtonToggled)
        self.radioButton10.toggled.connect(self.onRadioButtonToggled)
        self.radioButton11.toggled.connect(self.onRadioButtonToggled)
        self.radioButton12.toggled.connect(self.onRadioButtonToggled)
        
        vertical_align += self.vertical_gap + self.vert_gap
        self.entry_label = QtWidgets.QLabel(self)
        self.entry_label.setText("ENTRY")
        self.entry_label.setFont(label_font)
        self.entry_label.adjustSize()
        self.entry_label.move(self.left_margin + 5, vertical_align+5)
        
        
        self.entry_price_txt = QtWidgets.QLineEdit(self)
        self.entry_price_txt.move(100, vertical_align)
        self.entry_price_txt.setFont(text_input_font)
        self.entry_price_txt.resize(140, 40)
        self.entry_price_txt.setAlignment(QtCore.Qt.AlignLeft)
        self.entry_price_txt.setStyleSheet(
            "QLineEdit {border-radius:5px; border :1px solid black;}"
        )
        
        vertical_align += self.vertical_gap + self.vert_gap
        self.stop_label = QtWidgets.QLabel(self)
        self.stop_label.setText("STOP")
        self.stop_label.setFont(label_font)
        self.stop_label.adjustSize()
        self.stop_label.move(self.left_margin + 5, vertical_align+5)
        
        
        self.stop_price_txt = QtWidgets.QLineEdit(self)
        self.stop_price_txt.move(100, vertical_align)
        self.stop_price_txt.setFont(text_input_font)
        self.stop_price_txt.resize(140, 40)
        self.stop_price_txt.setAlignment(QtCore.Qt.AlignLeft)
        self.stop_price_txt.setStyleSheet(
            "QLineEdit {border-radius:5px; border :1px solid black;}"
        )
        
         # Button: Long Limit Entry
        vertical_align += self.vertical_gap + self.vert_gap
        self.long_entry = QtWidgets.QPushButton(self)
        self.long_entry.setText("Buy LIMIT")
        self.long_entry.move(self.left_margin, vertical_align)
        self.long_entry.clicked.connect(self.entry_long_on_limit)
        self.long_entry.setFont(button_font)
        self.long_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.long_entry.setIconSize(QtCore.QSize(40, 30))
        self.long_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.long_entry.setStyleSheet(
            "QPushButton {background-color : rgb(34,139,34);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(0,255,0);}"
        )
        
        # Button: Short Limit Entry
        self.short_entry = QtWidgets.QPushButton(self)
        self.short_entry.setText("Sell LIMIT")
        self.short_entry.move(self.btn_gap, vertical_align)
        self.short_entry.clicked.connect(self.entry_short_on_limit)
        self.short_entry.setFont(button_font)
        self.short_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.short_entry.setIconSize(QtCore.QSize(40, 30))
        self.short_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.short_entry.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )
        
        # Button: Long Limit Entry
        vertical_align += self.vertical_gap + self.vert_gap
        self.long_entry = QtWidgets.QPushButton(self)
        self.long_entry.setText("Buy STOP")
        self.long_entry.move(self.left_margin, vertical_align)
        self.long_entry.clicked.connect(self.long_stop_limit_order)
        self.long_entry.setFont(button_font)
        self.long_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.long_entry.setIconSize(QtCore.QSize(40, 30))
        self.long_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.long_entry.setStyleSheet(
            "QPushButton {background-color : rgb(34,139,34);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(0,255,0);}"
        )
        
        # Button: Short Limit Entry
        self.short_entry = QtWidgets.QPushButton(self)
        self.short_entry.setText("Sell STOP")
        self.short_entry.move(self.btn_gap, vertical_align)
        self.short_entry.clicked.connect(self.short_stop_limit_order)
        self.short_entry.setFont(button_font)
        self.short_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.short_entry.setIconSize(QtCore.QSize(40, 30))
        self.short_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.short_entry.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )
       
       
        # Button: Long Entry
        vertical_align += self.vertical_gap + self.vert_gap
        self.long_entry = QtWidgets.QPushButton(self)
        self.long_entry.setText("Buy On BID")
        self.long_entry.move(self.left_margin, vertical_align)
        self.long_entry.clicked.connect(self.entry_long_on_bid)
        self.long_entry.setFont(button_font)
        self.long_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.long_entry.setIconSize(QtCore.QSize(40, 30))
        self.long_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.long_entry.setStyleSheet(
            "QPushButton {background-color : rgb(34,139,34);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(0,255,0);}"
        )
        
        # Button: Short Entry
        self.short_entry = QtWidgets.QPushButton(self)
        self.short_entry.setText("Sell On BID")
        self.short_entry.move(self.btn_gap, vertical_align)
        self.short_entry.clicked.connect(self.entry_short_on_ask)
        self.short_entry.setFont(button_font)
        self.short_entry.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.short_entry.setIconSize(QtCore.QSize(40, 30))
        self.short_entry.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.short_entry.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )
        
        
        # Button: Cancel trades
        vertical_align += self.vertical_gap + self.vert_gap
        self.cancel_trades = QtWidgets.QPushButton(self)
        self.cancel_trades.setText("Cancel All")
        self.cancel_trades.move(self.left_margin, vertical_align)
        self.cancel_trades.clicked.connect(self.cancel_all_trades)
        self.cancel_trades.setFont(button_font)
        self.cancel_trades.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.cancel_trades.setIconSize(QtCore.QSize(40, 30))
        self.cancel_trades.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.cancel_trades.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )
        
        # Button: Close Positions
        self.close_trades = QtWidgets.QPushButton(self)
        self.close_trades.setText("Close Trades")
        self.close_trades.move(self.btn_gap, vertical_align)
        self.close_trades.clicked.connect(self.close_positions)
        self.close_trades.setFont(button_font)
        self.close_trades.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.close_trades.setIconSize(QtCore.QSize(40, 30))
        self.close_trades.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.close_trades.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )        
        
        # Button: Close Single Position
        vertical_align += self.vertical_gap + self.vert_gap
        self.close_single_position = QtWidgets.QPushButton(self)
        self.close_single_position.setText("Break Even")
        self.close_single_position.move(self.left_margin, vertical_align)
        self.close_single_position.clicked.connect(self.break_even)
        self.close_single_position.setFont(button_font)
        self.close_single_position.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        self.close_single_position.setIconSize(QtCore.QSize(40, 30))
        self.close_single_position.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.close_single_position.setStyleSheet(
            "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        )
        
        # Button: Reverse Positions
        # self.reverse_trades = QtWidgets.QPushButton(self)
        # self.reverse_trades.setText("Reverse")
        # self.reverse_trades.move(self.left_margin, vertical_align)
        # self.reverse_trades.clicked.connect(self.reverse_positions)
        # self.reverse_trades.setFont(button_font)
        # self.reverse_trades.setFixedSize(QtCore.QSize(self.btn_width, self.btn_height))
        # self.reverse_trades.setIconSize(QtCore.QSize(40, 30))
        # self.reverse_trades.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # self.reverse_trades.setStyleSheet(
        #     "QPushButton {background-color : rgb(220,20,60);  border-radius:10px; border :2px solid black; color: white;} QPushButton::pressed {background-color : rgb(250,128,114);}"
        # )     
    
    def onRadioButtonToggled(self):
        # Check which radio button is selected
        if self.radioButton1.isChecked():
            self.symbol = "US500.cash"
            self.dollor_value = 1
            self.spread = round(self.get_spread_price(), 2) # 1.0
        elif self.radioButton2.isChecked():
            self.symbol = "UK100.cash"
            self.dollor_value = round(1/self.get_exchange_price("GBPUSD"), 4)
            self.spread = round(self.get_spread_price(), 2) # 4.0
        elif self.radioButton3.isChecked():
            self.symbol = "HK50.cash"
            self.dollor_value = round(1/self.get_exchange_price("USDHKD"), 4)
            self.spread = round(self.get_spread_price(), 2) # 10.0
        elif self.radioButton4.isChecked():
            self.symbol = "JP225.cash"
            self.dollor_value = round(1/self.get_exchange_price("USDJPY"), 4)
            self.spread = round(self.get_spread_price(), 2) # 12.0
        elif self.radioButton5.isChecked():
            self.symbol = "AUS200.cash"
            self.dollor_value = self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread_price(), 2)
        elif self.radioButton6.isChecked():
            self.symbol = "US100.cash"
            self.dollor_value = 1
            self.spread = round(self.get_spread_price(), 2)
        elif self.radioButton7.isChecked():
            self.symbol = "AUDNZD"
            self.dollor_value = (1/self.get_exchange_price("AUDNZD")) * self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread_price(), 5)
        elif self.radioButton8.isChecked():
            self.symbol = "USDJPY"
            self.dollor_value = 1/self.get_exchange_price("USDJPY")
            self.spread = round(self.get_spread_price(), 3)
        elif self.radioButton9.isChecked():
            self.symbol = "USDCHF"
            tick_price = self.get_exchange_price("USDCHF")
            self.dollor_value = 1/tick_price
            self.spread = round(self.get_spread_price(), 5)
        elif self.radioButton10.isChecked():
            self.symbol = "AUDJPY"
            self.dollor_value = (1/self.get_exchange_price("AUDJPY")) * self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread_price(), 3)
        elif self.radioButton11.isChecked():
            self.symbol = "XAUUSD"
            # Added 2, Since it was picking the whole value
            self.dollor_value = 2/self.get_exchange_price("XAUUSD")
            self.spread = round(self.get_spread_price(), 3)
        elif self.radioButton12.isChecked():
            self.symbol = "EURUSD"
            self.dollor_value = self.get_exchange_price("EURUSD")
            self.spread = round(self.get_spread_price(), 3)
    
    def entry_long_on_bid(self):
        self.long_limit_and_bid_orders("bid_ask")
        
    def entry_short_on_ask(self):
        self.short_limit_ask_orders("bid_ask")
        
    def entry_long_on_limit(self):
        self.long_limit_and_bid_orders("limit")
        
    def entry_short_on_limit(self):
        self.short_limit_ask_orders("limit")
    
    def get_mid_price(self):
        ask_price = mt.symbol_info_tick(self.symbol).ask
        bid_price = mt.symbol_info_tick(self.symbol).bid
        diff_price = (ask_price - bid_price)/2
        
        if self.symbol in self.currencies:
            round_factor = 4
            
            if self.symbol in ["XAUUSD"]:
                round_factor = 2
            
            bid_price = round((bid_price + diff_price), round_factor)
            ask_price = round((ask_price - diff_price), round_factor)
        else:
            bid_price = round((bid_price + diff_price) * 10)/10
            ask_price = round((ask_price - diff_price) * 10)/10
        
        print("BID: ", bid_price, " ASK: ", ask_price)
        return bid_price, ask_price
    
    def get_exchange_price(self, exchange):
        ask_price = mt.symbol_info_tick(exchange).ask
        bid_price = mt.symbol_info_tick(exchange).bid
        exchange_rate = round((bid_price + ask_price)/2, 4)
        return exchange_rate
    
    
    def get_spread_price(self):
        ask_price = mt.symbol_info_tick(self.symbol).ask
        bid_price = mt.symbol_info_tick(self.symbol).bid
        spread = (ask_price - bid_price)
        return spread
    
    def get_limit_price(self):
        limit_price = float(self.entry_price_txt.text())
        return limit_price
    
    def get_stop_price(self):
        stop_price = round(float(self.stop_price_txt.text()), 4)
        return stop_price
    
    def calculate_slots(self, points_in_stop):
        positions = self.risk/(points_in_stop * self.dollor_value)
        return float(positions)
        
    
    def split_positions(self, x):
        if x >= 1:
            # Round x since we need round numbers
            x = round(x)
            remaining = x%2
            if remaining == 0:
                split = x/2
                print(float(split), float(split))
                return float(split), float(split)
            if remaining == 1:
                split = math.floor(x/2)
                print(float(split), float(split+1))
                return float(split), float(split+1)
        else:
            split = round(x/2, 2)
            print(float(split), float(split))
            return float(split), float(split)
        

    def long_stop_limit_order(self):
        entry_price = self.get_limit_price()
        stop_price = self.get_stop_price() - self.spread
        
        if stop_price > entry_price:
            raise Exception("Long entry not valid!")
        
        if self.symbol in self.currencies:
            points_in_stop = round(entry_price - stop_price, 5)
            position_size = round(self.calculate_slots(points_in_stop)/100000, 2)
        else:
            points_in_stop = round(entry_price - stop_price)
            position_size = self.calculate_slots(points_in_stop)
        
        
        target_price1 = entry_price + 2*points_in_stop
        target_price2 = entry_price + points_in_stop
        
        position1, position2 = self.split_positions(position_size)
        
        response = self.trade_confirmation(points_in_stop, position_size, target_price1)
        
        
        if response:
            request1 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position1, # FLOAT
                "type": mt.ORDER_TYPE_BUY_STOP_LIMIT,
                "price": entry_price,
                "stoplimit": entry_price - self.spread,
                "sl": stop_price, # FLOAT
                "tp": target_price1, # FLOAT
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            request2 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position2, # FLOAT
                "type": mt.ORDER_TYPE_BUY_STOP_LIMIT,
                "price": entry_price,
                "stoplimit": entry_price - self.spread,
                "sl": stop_price, # FLOAT
                "tp": target_price2, # FLOAT
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            res1 = mt.order_send(request1)
            self.order_log(res1)
            res2 = mt.order_send(request2)
            self.order_log(res2)
            
    def order_log(self, result):
        if result.retcode != mt.TRADE_RETCODE_DONE:
            error_string = f"code: {result.retcode}, reason: {result.comment}"
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText(error_string)
            msgBox.exec()
        else:
            print(f"Order placed successfully!")

    def long_limit_and_bid_orders(self, type):
        if type == "limit":
            entry_price = self.get_limit_price()
        elif type == "bid_ask":
            entry_price, _ = self.get_mid_price()
        else:
            raise Exception("Type not defined!")
        
        stop_price = self.get_stop_price() - self.spread
        
        if stop_price > entry_price:
            raise Exception("Long entry not valid!")
        
        if self.symbol in self.currencies:
            points_in_stop = round(entry_price - stop_price, 5)
            position_size = round(self.calculate_slots(points_in_stop)/100000, 2)
        else:
            points_in_stop = round(entry_price - stop_price)
            position_size = self.calculate_slots(points_in_stop)
        
        target_price1 = entry_price + 2*points_in_stop
        target_price2 = entry_price + points_in_stop
        
        position1, position2 = self.split_positions(position_size)
        
        response = self.trade_confirmation(points_in_stop, position_size, target_price1)
        
        if response:
            request1 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position1,
                "type": mt.ORDER_TYPE_BUY_LIMIT,
                "price": entry_price,
                "sl": stop_price,
                "tp": target_price1, # FLOAT
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            request2 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position2,
                "type": mt.ORDER_TYPE_BUY_LIMIT,
                "price": entry_price,
                "sl": stop_price,
                "tp": target_price2,
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            
            res1 = mt.order_send(request1)
            self.order_log(res1)
            res2 = mt.order_send(request2)
            self.order_log(res2)
    

    def short_stop_limit_order(self):
        entry_price = self.get_limit_price()
        stop_price = self.get_stop_price() + self.spread
        
        if stop_price < entry_price:
            raise Exception("Short entry not valid!")
        
        if self.symbol in self.currencies:
            points_in_stop = round(stop_price - entry_price, 5)
            position_size = round(self.calculate_slots(points_in_stop)/100000, 2)
        else:
            points_in_stop = round(stop_price - entry_price)
            position_size = self.calculate_slots(points_in_stop)
        
        target_price1 = entry_price - 2*points_in_stop
        target_price2 = entry_price - points_in_stop
        
        position1, position2 = self.split_positions(position_size)
        response = self.trade_confirmation(points_in_stop, position_size, target_price1)
        
        if response:
            request1 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position1, # FLOAT
                "type": mt.ORDER_TYPE_SELL_STOP_LIMIT,
                "price": entry_price,
                "stoplimit": entry_price + self.spread,
                "sl": stop_price, # FLOAT
                "tp": target_price1, # FLOAT
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            request2 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position2, # FLOAT
                "type": mt.ORDER_TYPE_SELL_STOP_LIMIT,
                "price": entry_price,
                "stoplimit": entry_price + self.spread,
                "sl": stop_price, # FLOAT
                "tp": target_price2, # FLOAT
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }

            res1 = mt.order_send(request1)
            self.order_log(res1)
            res2 = mt.order_send(request2)
            self.order_log(res2)
            

    def short_limit_ask_orders(self, type:str):
        if type == "limit":
            entry_price = self.get_limit_price()
        elif type == "bid_ask":
            entry_price, _ = self.get_mid_price()
        else:
            raise Exception("Type not defined!")
        
        stop_price = self.get_stop_price() + self.spread
        
        if stop_price < entry_price:
            raise Exception("Short entry not valid!")
        
        if self.symbol in self.currencies:
            points_in_stop = round(stop_price - entry_price, 5)
            position_size = round(self.calculate_slots(points_in_stop)/100000, 2)
        else:
            points_in_stop = round(stop_price - entry_price)
            position_size = self.calculate_slots(points_in_stop)
        
        target_price1 = entry_price - 2*points_in_stop
        target_price2 = entry_price - points_in_stop

        position1, position2 = self.split_positions(position_size)
        response = self.trade_confirmation(points_in_stop, position_size, target_price1)
        
        if response:
            request1 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position1,
                "type": mt.ORDER_TYPE_SELL_LIMIT,
                "price": entry_price,
                "sl": stop_price,
                "tp": target_price1,
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }
            
            request2 = {
                "action": mt.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": position2,
                "type": mt.ORDER_TYPE_SELL_LIMIT,
                "price": entry_price,
                "sl": stop_price,
                "tp": target_price2,
                "comment": "python script open",
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_RETURN,
            }

            res1 = mt.order_send(request1)
            self.order_log(res1)
            res2 = mt.order_send(request2)
            self.order_log(res2)

    def trade_confirmation(self, points_in_stop, position_size, target_price1):
        input_string = f"{self.symbol} with ${self.risk}<br> Dollar Value : ${self.dollor_value} <br>Risk ({points_in_stop})pips <br>Positions {position_size}<br> Target @ {target_price1}"
            
        reply = QMessageBox.question(self, 'Trade Confirmation!', input_string,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
           return True
        else:
            return False
        
    def cancel_all_trades(self):
        # Get a list of all open positions
        positions = mt.orders_get()

        # Iterate through the positions and close each one
        for position in positions:
            if position.symbol == self.symbol:
                request = {
                    "action": mt.TRADE_ACTION_REMOVE,
                    "order": position.ticket,
                }

                # Send the trade request
                result = mt.order_send(request)

                if result.retcode != mt.TRADE_RETCODE_DONE:
                    print(f"Failed to cancel order {position.ticket}, error code: {result.retcode}, reason: {result.comment}")
                else:
                    print(f"Order {position.ticket} cancelled successfully.")
    
    
    def close_positions(self):
        # Get open positions
        positions = mt.positions_get()

        for obj in positions: # we iterate through all open positions
            if obj.symbol == self.symbol:
                if obj.type == 1: # if order type is a buy, to close we have to sell
                    order_type = mt.ORDER_TYPE_BUY
                    price = mt.symbol_info_tick(obj.symbol).bid
                else:                   # otherwise, if order type is a sell, to close we have to buy
                    order_type = mt.ORDER_TYPE_SELL
                    price = mt.symbol_info_tick(obj.symbol).ask
                
                close_request = {
                    "action": mt.TRADE_ACTION_DEAL,
                    "symbol": obj.symbol,
                    "volume": obj.volume,
                    "type": order_type,
                    "position": obj.ticket,
                    "price": price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": 'Close trade',
                    "type_time": mt.ORDER_TIME_GTC,
                    "type_filling": mt.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
                }
                
                result = mt.order_send(close_request) # send order to close a position
                
                if result.retcode != mt.TRADE_RETCODE_DONE:
                    print("Close Order "+obj.symbol+" failed!!...Error Code: "+str(result.retcode))
                else:
                    print("Order "+obj.symbol+" closed successfully")

    
    def break_even(self):
        
        # Get open positions
        positions = mt.positions_get()
        
        for obj in positions:
            if obj.symbol == self.symbol:
                if obj.type == 1:
                    adjusted_stop = obj.price_open - 0.25
                else:                   
                    adjusted_stop = obj.price_open + 0.20
            
                modify_request = {
                    "action": mt.TRADE_ACTION_SLTP,
                    "symbol": obj.symbol,
                    "volume": obj.volume,
                    "type": obj.type,
                    "position": obj.ticket,
                    "sl": adjusted_stop,
                    "tp": obj.tp,
                    "comment": 'Break Even',
                    "magic": 234000,
                    "type_time": mt.ORDER_TIME_GTC,
                    "type_filling": mt.ORDER_FILLING_FOK,
                    "ENUM_ORDER_STATE": mt.ORDER_FILLING_RETURN,
                }
                
                result = mt.order_send(modify_request) # send order to close a position
                
                if result.retcode != mt.TRADE_RETCODE_DONE:
                    print("Close Order "+obj.symbol+" failed!!...Error Code: "+str(result.retcode))
                else:
                    print("Order "+obj.symbol+" modified successfully")
        

    def reverse_positions(self):
        # Get open positions
        positions = mt.positions_get()
        
        for obj in positions:
            if obj.type == 1:
                self.close_positions()
                self.long_entry()
            else:                 
                self.close_positions()             
                self.short_entry()
        
def window():
    app = QApplication(sys.argv)
    app.setApplicationName("FTMO")
    win = MyWindow()
    win.show()
    sys.exit(app.exec_())


window()
