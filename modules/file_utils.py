class FileUtils:
    def __init__(self) -> None:
        pass
    
    def log_writer(self, trade_time, write_line, write_mode="a", sep="\t"):
        """
        Write the logs

        Args:
            input (str): Input String
            trade_time (str): Keep the time format as follows : "%Y%m%d %H:%M:%S"
            write_mode (str, optional): _description_. Defaults to "a".
        """
        date_split = trade_time.split(" ")
        date = date_split[0]
        hour = int(date_split[-1].split(":")[0])
        
        # When the input is list, convert to string and joing by commma
        if isinstance(write_line, list):
            write_line = ','.join([str(i) for i in write_line])
        
        with open("session.logs", write_mode) as f:
            # Prepend the time
            f.write(f"{trade_time}{sep}{write_line}\n")
            f.close()
    
    def equity_collector(self, file_name, date_time, equity):
         with open(f"{file_name}.csv", "a") as f:
            f.write(f"{date_time},{equity}\n")
            f.close()
            
if __name__ == "__main__":
    obj = FileUtils("/")
    # obj.log_writer("testing,adfad")
    obj.equity_collector("asdf", 9080)