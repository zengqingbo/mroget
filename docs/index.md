# MRO get and process system -A big data approach

# 1	Analysis model

## 1.1	Back ground 
  Recently, we are handling MRO files (Measurement Result Recording) in the LTE network.  In every hour, we will collect about   thousands of files in the capacity of 2T in my project.  After we have parsed the Xml files we will get about 20 billion sample points every day.  Since we have so many files to handle, we have used the multi-process technology via multi-processors of a single linux computer. Yet the linux computers has only 24 processors, we wish to have several computers to handle the files. 

## 1.2	Hardware environment
  In the above diagram, we can see that we have three kinds of computers.

![diagram-1](diagram/1-computers.png?raw=True "diagram-1")

1. *Filer getter machine* : It will connect to various LTE OMC servers, scanning the new arriving MRO files in certain directory and transfer the new arriving files to the local file machine. At present we have just 1 computer.
2. *File parser machine* : The new arriving files will be distributed to the file parser machine. The file parser process will fetch the new arriving files , parse the xml files, transfer the file stream into object stream, pick up the required data items and transfer the object stream into the CSV format file stream .  All the required information fields will be recorded in the csv file. In our plan, we will use 7 computers to parse the files.
3. *Database machine* : All the required information fields will future be uploaded into the database. We choose Green-plums as the database engine.  At present, we have 5 computers to run the Green-plums database instances.

## 1.3	The project overview

### 1.3.1	Code structure

![diagram-2](diagram/2-code_structure.png?raw=True "diagram-2")

  From  the above diagram, we can see that all the package in the project .now let’s have a look at it.
1. config.py ： It is the gloal configuration file , including the database connection, the Target location, and  time difference configuration
2. mrnicfg.csv ： The configuration information of external FTP server ( The MRO file server)
3. *filegetter_mr.py* ：  The main program to fetch MRO file from the external FTP server ( The MRR file server)
4. ftpext.py : A third party component to fetch files from the external FTP server. It will provide service for the component filegetter_mr.py 
5. *mrofileSender.py* ： The main program to distributed the new arriving file and handle it. 
6. mroHandler.py ：MRO single file process component
7. mroparser5.py ： MRO single file parsing component
8. mroCounter.py : MRO Post analysis of special sample point  statistical components

### 1.3.2	Background of the project
  In the year 2015, the LTE network starts to operate in the market, the MRO data and related application are introduced in the *Wireless-Network-Management-System*. Since the MRO data is associated with the User equipment call record, The total number of the data is nearly 100 billion a day.  The integrator of the  *Wireless-Network-Management-System* choose the Hadoop and Hive solution. The  solution is *very low* in performance, *very complex* to maintain, and very difficult to introduce new functionality.
  In the year 2016, the scale of the MRO data is about 12 T, therefore we hope to find a more efficiency solution。 After extensive consultation and research， we finally decide to choose a multi-core calculation approach . We choose the python and postgres-sql as the basic tools. It took us 48 hours to process all the data in a single computer with 32 cores.  In every second ,it will process 90 thousand records. In this prototype program, we must prepare all the input files manually.  It is not proper for the everyday processing, therefore we wish to optimize the solution and we will use a real-time processing solution.
  So we hope to develop a real-time file processing system, to fetch MRO files from various external FTP server, parsing the MRO files to get the requirement information structure, ready the temporary result file, and batch upload the result file to the database.
  The global view of the project can be seen in the diagram below:

![diagram-3](diagram/3-application_context.png?raw=True "diagram-3")

  Form the above diagram we can see that the application context of the project. We have the following procedure:
1.in every hour, the file getter will search in the external MRO FTP server, check the source MRO file directory and fetch the new arriving files. The file getter will ready the new arriving files in local file system.
2.The MRO file handler will process the new arriving files one by one, transfer the file stream into the intermediate stream, get the required information structure, and finally transfer the intermediate stream into the result CSV file.
3.Finally, the result  CSV file will be uploaded to a Green-plum database in a batch mode.

### 1.3.3	Big data problem
Although the Use-Case is not complex, the data volume is relative big. So we have the following problem:
1. Everyday，we will collect about   thousands of files in the capacity of 2T in my project.  After we have parsed the Xml files we will get about 20 billion sample points.
2. In such application context, we need several machines to handle the massive MRO files. We need a distributed computing frame work to handle problem.
3. In the IPO point view， the input data comes from the external FTP servers, and the output data will be uploaded to the external Green-plum database. There are might be errors in the boundary of the system. Fault handling will be a difficult job in the application. And in t he multi-machine and multi-processor environment, fault handling will be much complex.
4. Dynamic load balance。Since we use multi-machine solution, the processors of each machine might be different. For example, we need several computers to handle the MRO files. An adaptive dynamic load balance approach is required.
5. system installation and maintenance. Since we use multi-machine solution, It will be very bother to install the software in various machine and maintain the cluster.
So we hope to find a good approach the design the system, that is why we setup a GIT .

### 1.3.4	Use case model
  Now let’s have look at the Use –case model. The use-case diagram can be seen below.

![diagram-4](diagram/4-use_case.png?raw=True "diagram-4")

  In the above use-case diagram, we have two main use-cases, get MRO File and handle MRO file. 
1. get MRO file: the file getter will scanning all the external FTP servers to discover the new arrived MRO files and fetch them to local File directory. Since it is not complex job, a single machine can handle current file scale.
2. handle MRO file: when new arriving file are located in local File directory,  it will be transferred into intermediate stream and required information structure will be picked up. The result will be transferred into an CSV file.  This use-case is a very complex job and processor consuming, we need 7 machines to process the current file scale.

#### 1.3.4.1	Get MRO file
  Now ,let’s have a look at the event flow of the usecase.
1. The timer will log on each of the MRO_FTP servers every five minutes.
2. The timer will scan certain directory according to the date and time. The timer will fetch the file list of current directory and transfer the result to the memory.
3. The timer will compare the file-list of current FTP_Server and the file-list which the timer has already collected; and figure out the new arrived MRO files.
4. The timer will start to fetch the new arrived files one by one. When the timer has fetched a file ,it will create a new makeup file in local file system to make sure the new MRO file has been transferred successful to local .
5. When all the files have been transferred to local directory, the current job has been finished.

#### 1.3.4.2	Handle mro file
  Here comes the event flow of the use-case handle MRO file.
1. The timer will scan local database to verify the new arriving files in every 2 minutes.  There is a table in local postgres-sql database to record the new arriving files.
2. the file sender will fetch the new arriving files, distinguish the file format and vender , and route the new arriving files to associated file handler.
3. The corresponding file handler will wake up the multi-processing pool and hand the files in a parallel mode. When the file is parsed a result csv file will be prepared in the destination file directory. 
When all the files are processed, the use case is finished. 

### 1.3.5	Domain object model

![diagram-5](diagram/5-domain_object.png?raw=True "diagram-5")

  Since this project is on the LTE network, let’s have a closer look at the domain object of the project.
  From the picture above，we can seen the main domain object. 
1. E-nodeB： The E-nodeB is the basic hardware component in the 4G LTE network. A LTE network is composed of several E-nodeBs.  The E-nodeB will provide access service for all the mobile phones, allocate physical channels to the mobile phone to send or receive data from the network, and take the measurement report for each of the mobile phone which is in the connecting mode. The E-nodeB will generate MRO files every hour and transfer it to the OMC Server.
2. E-utrancell： The E-urtrancell is the basic software component in the 4G LTE network. It is the basic service unit in the network. Each of the E-utrancell will cover a certain spatial area (polygon). When the mobile user is located in this area, he will register in the cell.
3. OMC FTP_ SERVER： The OMC FTP_SERVER is the service gateway in the LTE network, it will receive the MRO files which the OMC has collected and storage them in his local file system.
4. MRO_files： It is used to record all the mobile measurement reports of the user equipment which is belong to the E-NODEB service area. The MRO report is generated periodicity (in general every 500 ms) while the user equipment is in the connecting mode. We can see the amount of the report will be very large.
5. SAMPLE: if we look inside the MRO_files , we could see several Sample points for each of the User Equipment. Since the information structure of the sample is really complex, we could future use the composition structure to model the sub-object. 
  In our project, Sample object is the key object in the application. We will have a closer look at it. 
The Sample object consists of three objects, the GPSinfo, the SCinfo, and the Ncinfo. For an Sample object, it consists of three parts. 
1. GPS info. With the help of spatial analysis, we could estimate the Geographic information of each sample point in a acceptance Accuracy. Therefore each of the sample object will have an identical GPS info.  
2. SC info.  When the User-Equipment are sending and receiving data, it will first select a serving cell to login on. It will measure the network information of the serving cell. All these information will be recorded on the object SCinfo.
3. NC info. When the User-Equipment are sending and receiving data, It will  measure the network information of not only the serving cell, but also the neighbor cell. As several neighbor cell will be recorded, we use a sub-object to model the NC info.

### 1.3.6	Robust analysis 
  In the robust analysis procedure, we wish to find a reliable object model to support the use case. Theoretically, in the process of Robust analysis, we refined the domain object model without consideration of the implementation environment, including the programming language, the operation system and the middle ware.  we can understand the system better via the analysis model.

![diagram-6](diagram/6-analysis_object.png?raw=True "diagram-6")

From the above diagram, we can see that ,we have three type of object.
1、interface object. Here we have one interface object, the filegetter. it will visit the external OMC_FTP_server to get the new arriving MRO_files.
2、Control object. The control will handle complex logic. Here we have the filesender , and the file handler.
3、Entity object: The entity object is associated the domain object model. And we have four Entity object.
1) the file_list, it represents the file item of the MRO_file. 
2) the MRO_file: it is a xml format file, which is fetched by the object filegetter.
3)sample:  when the user Equipment(mobile phone) is  in the connecting mode, it will upload a report to the system in certain time interval.  We can model such report as the object sample. 
4）The Resultfile： it is a CSV format file , which is generated bu the object file handler.

### 1.3.7	Design model
  Now let’s have a look at the Design model of the final object.

![diagram-7](diagram/7-the_component_model.png?raw=True "diagram-7")

#### 1.3.7.1	Config.py 
In the object, we have 4 parameters, let’s have a look at it.
1、PG_CONN_TEXT： the postgres-sql database connection information.
2、MRO_PATH: the local file system directory to Temporary storage the MRO file
3、CSV_PATH： the local file directory to Temporary storage the result file. 
4、DELTA_HOURS:

#### 1.3.7.2	Mrnicfg.csv
  In the configuration file, we will describe the parameters of the external OMC_FTP_server.  For example the ip_address , the user name and the password.

#### 1.3.7.3	filegetter_mr.py
  since this component is not very complex, we just represent the component diagram here. It will fetch the MRO files from external OMC_FTP_server, and put them in the local file system as the parameter MRO_PATH defined. 
  See the component diagram below:

![diagram-8](diagram/8-the_filgetter_model.png?raw=True "diagram-8")

  Form the above diagram，we can see the main object model of the component：
  entity object： There are 3 entity object , which are the omcinfo，mrnicfg.csv and the MRO_file. The domain object omcinfo record the information structure of the FTP server. The object omcinfo exists in the memory. The object mrnicfg.csv contains the same information structure of the object of omcinfo, yet it is in the format of file system. And the object MRO_file  represents the files collected from the FTP_servers. 
  Boundary object：In the project of the FTP getter component, there are 4 boundary objects, including the multi-pool，getMROnicfg，ftpDL，ftpPush. Let’s have a look at the function of the object. 
1、The object multi-pool will manage the Computing resources of the hardware, to obtain the Parallel Computing ability.
2、 The object FtpDl and FtpPush will utilize the function of the Plugin FTPEXT, to download and transfer the files from various Servers . 
3、The object getMROnicfg will read the external CSV file and transfer the file stream into intermediate stream.
  Control object：There are two control objects in the project. The object MROFilegetter will manage the multi-thread framework, and process the task in parallel. The object Nigetter will visit the remote FTP server and scanning the new arrived files.    
  Form the picture above, we can see that with the three kind of object , we can easily de-composite the component into smaller part, and we can easily manage the project.
  Here we use a multi-process technology to fetch the files faster,see the configuration below:
p = Pool(2)

#### 1.3.7.4	Ftpext.py
A third party component to fetch files from the external FTP server. It will provide service for the component filegetter_mr.py.
For the detailed info see the below link:
https://www.smartftp.com/static/Products/SmartFTP/RFC/x-dupe-info.txt


#### 1.3.7.5	 Filesender

![diagram-9](diagram/9-the_object_view_of_file_senderl.png?raw=True "diagram-9")

First we have a look at the control object. 
1、filesender:it will look up the new arriving xml files , identify the vender of the XML files ( There five venders in my province,  we choose different approaches to handle the MRO files from different vender.) 
2、handleFile： if the MRO files is two-layer compressed file format, we will choose the component handleFile to process the file. The logic to handle the two-layer compressed file is relative complex.

![diagram-10](diagram/10-the_two_lay_zip_file.png?raw=True "diagram-10")

3、handle singlefile： if the MRO files is one-layer compressed file format, we will choose the component handle singlefile to process the file. The logic to handle the one-layer compressed file is relative simple 
We have three interface object:
1、FilelistRecord(path): it will scan the local file system of the existing MRO files, and copy the list of existing MRO files to a temp table in the database.
2、getvalidfilelist: it will verify the database to fetch the new arrived MRO files. The information structure will be copied to the object RS.
3、getnbcfgdict: it will visit the database to get the vender associated information.  And the information structure will be copied to the object nbccfg.
The we have three  entity objects.
1、nbccfg： the object nbccfg will contain information structure of the LTE OMC FTP server, with the information structure the object Filesender will identity the vender of the MRR xml file, and the id of various omc-server which will future be used as the file segment identity in the local file system.

![diagram-11](diagram/11-nbcfg.png?raw=True "diagram-11")

2, RS: the object RS will contain the information structure of the new arrived files. 
3、file_list: it will record the new arrived MRO_files. It is consist of a temp-table and a table in the database.

![diagram-12](diagram/12-rs.png?raw=True "diagram-12")

With the information, we can identify the file directory of the new arrived file, the file name of the new arrived file, the nid of the new arrived file( the nid represent the source OMC-server which prepares the MRO files)
The above nine objects are the main components to handle the new arrived files. In summary the object fileSender works as the coordinator to schedule the new arrived MRO files, the object handleFile and handleSingleFile will work as the worker to process the new arrived MRO files according to the vender of the MRO files.

#### 1.3.7.6	handleFile
  if the MRO files is two-layer compressed file format, we will choose the component handleFile to process the file. The logic to handle the two-layer compressed file is relative complex. Let’s have a look at the component view of the handleFile.

![diagram-13](diagram/13-handle_file.png?raw=True "diagram-13")

In the above diagram , we will see the main procedure of the XML processing task.
1、 The object handleZipfile(filename ,nid) will first identify the file directory of the MRO files acoording to the input argument . 
2、the object handleZipfile(filename ,nid) will fetch target file and transfer the file stream into the object stream via the function ZIPfile(), we have the object myzip which is the object stream in the memory. In general, the object myzip is in the size of 1 G Byte. 
 3、the object handleZipfile(filename ,nid) will scan the object myzip,  identify all the sub-zip files and call the function of the multi-pool object to wake up various process to handle the subZIP file. 
 4、The object  handleSubZip(myzip,subname,nid)  will  parse the subZip file.  And the number of instance of the class handleSubZip(myzip,subname,nid)  depends on the number of processors of the local computer. 
        When all the sub-zip files are handled, the two layers compressed file is finished.

#### 1.3.7.7	Handlesinglefile()
if the MRO files is just one-layer compressed file format, we will choose the component handlesingleFile to process the file. The logic to handle the one-layer compressed file is relative simple. Let’s have a look at the component view of the handleFile.

![diagram-14](diagram/14-handlesinglefile.png?raw=True "diagram-14")

In this case , the logic is relative simple, we just call a object  handleMrofile（）to parse the file, which is a component form previous project.

#### 1.3.7.8	 Object reuse via the comositon mechanism

![diagram-15](diagram/15-code_reuse.png?raw=True "diagram-15")

Since we have various vender files to handle, we must design a flexible object structure with less code. So we reuse some code via the composition mechanism.  The  object relation can be seen in the above diagram
1、 the object Handlesubzip(myzip,subname,nid) is consist of the handlemrofile(fobj,nid) .  the object handleSinglefile is also consist of the object handlemrofile(fobj,nid).
2、 the object handlemrofile(fobj,nid) is consist of the object MRO handler(fobj,nid)
3、The object MRO handler(fobj,nid)  is consist of  the object MROparser5 and the object mrocounter

#### 1.3.7.9	Mrofilehandler
The object  MRofilehandler  will parser the xml format  XMR file and ready the result files.

![diagram-16](diagram/16-MROhandler.png?raw=True "diagram-16")

in the above example, we will describe the processing sequence.
1、first the object MRoparser5 will parse the intermediate stream fobj, pick up the required information field and creat a new object M, that is the key object in the application.
2、 second， the object MROcounter will process the object m and creat a new object C. 
3，finally the MROhandler will transfer the object m and object C to some CSV format file.  the directory is the CSV_PATH which comes form the config.py. 

#### 1.3.7.10	Object 2table
Here we have a very important object file_list , which is used to record the new arriving MRO files.  So let’s have a look at the table:
CREATE TABLE public.filelist_68_all
(
  run_server_name text,
  filename text,
  status boolean,
  nid integer
);

## 1.4	The problem we meet
1. schedule management component:  Now we just use the schedule of the linux os system, we hope to find a python component to manage the task.
2. the coordination of the File getter and the File parser: we have 1 computer to work as the File getter, and 7 computers to work as the File Parser. We still do not find a proper way to coordinate the 8 computers.
3. how to collecting the logs for the computers and process: in the distributing environment, it is so difficult to collect the log for the each of  control  component. For example, in the File parser computers, there are about 300 process to parse the files in concurrence. That will be difficult.

## 1.5	Future job
  In summary, this the design document of the project mroget version 0.5, we will try to find a next version which can handle the multi-machine  application easier.

