
# main.py
from server import mcp
# Import tools so they get registered via decorators
import tools.csv_tools
import tools.parquet_tools
import tools.research_tools
import tools.sqllite_explorer

def main():
    print("Hello from mcpworks!")

# Entry point to run the server
if __name__ == "__main__":
    #mcp.run()
    mcp.run(transport='stdio')

# if __name__ == "__main__":
#     main()
