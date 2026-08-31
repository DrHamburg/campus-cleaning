CREATE DATABASE campus_cleaning;
USE campus_cleaning;
-- 1. STAFF — Superclass
CREATE TABLE STAFF (
    Staff_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(150) NOT NULL,
    Phone_Number VARCHAR(30),
    Email VARCHAR(150) NOT NULL UNIQUE,
    Gender ENUM('Male', 'Female', 'Other'),
    Address VARCHAR(255),
    NID VARCHAR(30),
    Date_of_Joining DATE NOT NULL,
    Status ENUM('Active', 'Inactive') DEFAULT 'Active'
);
-- 2. SUPERVISOR — Subclass of STAFF
CREATE TABLE SUPERVISOR (
    Staff_ID INT PRIMARY KEY,
    Assigned_Floor INT NOT NULL,
    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID) ON DELETE CASCADE,
    CHECK (Assigned_Floor BETWEEN 1 AND 12)
);
-- 3. CLEANING_STAFF — Subclass of STAFF
CREATE TABLE CLEANING_STAFF (
    Staff_ID INT PRIMARY KEY,
    Assigned_Area VARCHAR(100) NOT NULL,
    Assigned_Block CHAR(1) NOT NULL,
    Supervisor_ID INT NOT NULL,
    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID),
    FOREIGN KEY (Supervisor_ID) REFERENCES SUPERVISOR(Staff_ID),
    CHECK (Assigned_Block BETWEEN 'A' AND 'H')
);
-- 4. CAMPUS_LOCATION 
CREATE TABLE CAMPUS_LOCATION (
    Location_ID VARCHAR(20) PRIMARY KEY,
    Block_Name CHAR(1) NOT NULL,
    Floor_No INT NOT NULL,
    Room_No VARCHAR(20) NOT NULL,
    Location_Type ENUM('Room', 'Lab', 'Washroom', 'Stairs') DEFAULT 'Room',
    Location_Status ENUM('Active', 'Inactive') DEFAULT 'Active',

    CHECK (Block_Name BETWEEN 'A' AND 'H'),
    CHECK (Floor_No BETWEEN 1 AND 12)
);
-- 5. SHIFT
CREATE TABLE SHIFT (
    Shift_ID INT AUTO_INCREMENT PRIMARY KEY,
    Shift_Name VARCHAR(50) NOT NULL,
    Start_Time TIME NOT NULL,
    End_Time TIME NOT NULL,
    Shift_Status ENUM('Active', 'Inactive') DEFAULT 'Active'
);
-- 6. ATTENDANCE
CREATE TABLE ATTENDANCE (
    Attendance_ID INT AUTO_INCREMENT PRIMARY KEY,
    Staff_ID INT NOT NULL,
    Shift_ID INT NOT NULL,
    Attendance_Date DATE NOT NULL,
    Check_In_Time TIME,
    Check_Out_Time TIME,
    Attendance_Status ENUM('Present','Absent','Late','On Leave') DEFAULT 'Present',
    Remarks VARCHAR(255),

    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID),
    FOREIGN KEY (Shift_ID) REFERENCES SHIFT(Shift_ID),
    UNIQUE (Staff_ID, Shift_ID, Attendance_Date)
);
-- 7. CLEANING_TASK
CREATE TABLE CLEANING_TASK (
    Task_ID INT AUTO_INCREMENT PRIMARY KEY,
    Staff_ID INT NOT NULL,
    Location_ID VARCHAR(20) NOT NULL,
    Shift_ID INT NOT NULL,
    Assigned_By INT NOT NULL,
    Task_Date DATE NOT NULL,
    Task_Status ENUM('Pending', 'In Progress', 'Completed', 'Cancelled') DEFAULT 'Pending',
    Completion_Time TIME,
    Remarks VARCHAR(255),

    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID),
    FOREIGN KEY (Location_ID) REFERENCES CAMPUS_LOCATION(Location_ID),
    FOREIGN KEY (Shift_ID) REFERENCES SHIFT(Shift_ID),
    FOREIGN KEY (Assigned_By) REFERENCES SUPERVISOR(Staff_ID)
);
-- 8. CLEANING_MATERIAL
CREATE TABLE CLEANING_MATERIAL (
    Material_ID INT AUTO_INCREMENT PRIMARY KEY,
    Material_Name VARCHAR(100) NOT NULL,
    Current_Stock INT DEFAULT 0,
    Reorder_Level INT DEFAULT 0,
    Material_Status ENUM('Available','Low Stock','Out of Stock') DEFAULT 'Available',
    CHECK (Current_Stock >= 0),
    CHECK (Reorder_Level >= 0)
);


-- 9. MATERIAL_HANDOUT
CREATE TABLE MATERIAL_HANDOUT (
    Handout_ID INT AUTO_INCREMENT PRIMARY KEY,
    Staff_ID INT NOT NULL,
    Issued_By INT NOT NULL,
    Handout_Date DATE NOT NULL,
    Usage_Purpose VARCHAR(255),
    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID),
    FOREIGN KEY (Issued_By) REFERENCES SUPERVISOR(Staff_ID)
);
-- 10. HANDOUT_ITEM
CREATE TABLE HANDOUT_ITEM (
    Handout_ID INT NOT NULL,
    Item_No INT NOT NULL,
    Material_ID INT NOT NULL,
    Quantity INT NOT NULL,
    Return_Status ENUM('Not Returned','Returned','Partially Returned') DEFAULT 'Not Returned',
    PRIMARY KEY (Handout_ID, Item_No),
    FOREIGN KEY (Handout_ID) REFERENCES MATERIAL_HANDOUT(Handout_ID) ON DELETE CASCADE,
    FOREIGN KEY (Material_ID) REFERENCES CLEANING_MATERIAL(Material_ID),
    CHECK (Quantity > 0)
);

-- 11. CLEANING_ISSUE
CREATE TABLE CLEANING_ISSUE (
    Issue_ID INT AUTO_INCREMENT PRIMARY KEY,
    Location_ID VARCHAR(20) NOT NULL,
    Task_ID INT,
    Reported_By INT NOT NULL,
    Issue_Date DATE NOT NULL,
    Issue_Type VARCHAR(100) NOT NULL,
    Description VARCHAR(255),
    Priority ENUM('Low', 'Medium', 'High') DEFAULT 'Medium',
    Issue_Status ENUM( 'Open','In Progress','Resolved') DEFAULT 'Open',
    Resolved_Date DATE,
    Resolution_Remarks VARCHAR(255),
    FOREIGN KEY (Location_ID) REFERENCES CAMPUS_LOCATION(Location_ID),
    FOREIGN KEY (Task_ID)  REFERENCES CLEANING_TASK(Task_ID),
    FOREIGN KEY (Reported_By) REFERENCES STAFF(Staff_ID)
);

-- 12. USER_ACCOUNT — Authentication
CREATE TABLE USER_ACCOUNT (
    User_ID INT AUTO_INCREMENT PRIMARY KEY,
    Staff_ID INT NOT NULL UNIQUE,
    University_Email VARCHAR(150) NOT NULL UNIQUE,
    Password_Hash VARCHAR(255) NOT NULL,
    Role ENUM('CLEANING_STAFF', 'SUPERVISOR') NOT NULL,
    Account_Status ENUM('ACTIVE','INACTIVE','SUSPENDED') DEFAULT 'ACTIVE',
    Must_Change_Password BOOLEAN DEFAULT TRUE,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Last_Login TIMESTAMP NULL,
    FOREIGN KEY (Staff_ID) REFERENCES STAFF(Staff_ID)
);

-- DROP DATABASE IF EXISTS campus_cleaning;  
-- CREATE DATABASE campus_cleaning;
-- USE campus_cleaning;

