# MRO get and process system -A big data approach

# 1	Analysis model

## 1.1	Back ground 
  Recently, we are handling MRO files (Measurement Result Recording) in the LTE network.  In every hour, we will collect about   thousands of files in the capacity of 2T in my project.  After we have parsed the Xml files we will get about 20 billion sample points every day.  Since we have so many files to handle, we have used the multi-process technology via multi-processors of a single linux computer. Yet the linux computers has only 24 processors, we wish to have several computers to handle the files. 

## 1.1	Hardware environment
  In the above diagram, we can see that we have three kinds of computers.
![diagram-1](diagram/1-computers.png?raw=True "diagram-1")
