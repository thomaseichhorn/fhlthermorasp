// compile with:
// g++ monitor.cc -o monitor -L/usr/local/lib -lwiringPi

#include <cmath>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <linux/i2c-dev.h>
#include <sstream>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <vector>
#include <wiringPi.h>

#define MAXTIMINGS 85

// w1 ID - 10 is considered the max usable count
char dev[20][16];

// w1 path
char path[] = "/sys/bus/w1/devices";

// found devices
int w1count = 0;

// write individual sensor output for mrtg
bool mrtgoutput = false;

// returns the current time in a formatted string
std::string gettime ( )
{
    time_t rawtime;
    struct tm * timeinfo;
    time ( &rawtime );
    timeinfo = localtime ( &rawtime );
    char timebuffer [90];
    strftime ( timebuffer, 80, "%Y-%m-%d %H:%M:%S", timeinfo );
    return ( timebuffer );
}

// read a dht11
std::string read_dht11 ( int DHTPIN )
{
    int dht11_dat[5] = { 0 };
    uint8_t laststate = HIGH;
    uint8_t counter = 0;
    uint8_t j = 0;

    // pull pin down for at least 18 milliseconds
    pinMode ( DHTPIN, OUTPUT );
    digitalWrite ( DHTPIN, LOW );
    delay ( 20 );

    // then pull it up for 40 microseconds
    digitalWrite ( DHTPIN, HIGH );
    delayMicroseconds ( 40 );

    // prepare to read the pin
    pinMode ( DHTPIN, INPUT );

    // detect change and read data
    for ( int i = 0; i < MAXTIMINGS; i++ )
    {
	counter = 0;
	while ( digitalRead ( DHTPIN ) == laststate )
	{
	    counter++;
	    delayMicroseconds ( 1 );
	    if ( counter == 255 )
	    {
		break;
	    }
	}
	laststate = digitalRead ( DHTPIN );

	if ( counter == 255 )
	{
	    break;
	}

	// ignore first 3 transitions
	if ( ( i >= 4 ) && ( i % 2 == 0 ) )
	{
	    // shove each bit into the storage bytes
	    dht11_dat[j / 8] <<= 1;
	    if ( counter > 16 )
	    {
		dht11_dat[j / 8] |= 1;
	    }
	    j++;
	}
    }

    char retstr[32];
    // check that we read 40 bits ( 8bit x 5 ) and verify checksum in the last byte
    if ( ( j >= 40 ) && ( dht11_dat[4] == ( ( dht11_dat[0] + dht11_dat[1] + dht11_dat[2] + dht11_dat[3] ) & 0xFF ) ) )
    {
	snprintf ( retstr, sizeof ( retstr ), "%d.%02d %d.%02d", dht11_dat[0], dht11_dat[1], dht11_dat[2], dht11_dat[3] );
	return ( retstr );
    }
    else
    {
	//std::cout << " Fail for DHT11 pin " << DHTPIN << "! Output is " << dht11_dat[0] << " " << dht11_dat[1]<< " " << dht11_dat[2]<< " " << dht11_dat[3] << " !" << std::endl;
	return ( "X" );
    }
}

// reads 1-Wire sensors
std::string read_w1 ( )
{
    double thetemp[20] = { 0.0 };
    std::string retstr = "";
    for ( int i=0; i<w1count; i++ )
    {
	// path to device
	char devPath[128];

	// data from device
	char buf[256];

	// temperature in degrees C * 1000 reported by device 
	char tmpData[6];

	ssize_t numRead;
	sprintf ( devPath, "%s/%s/w1_slave", path, dev[i] );
	int fd = open ( devPath, O_RDONLY );
	if ( fd == -1 )
	{
	    // read error
	    return ( "X" );
	}
	while ( ( numRead = read ( fd, buf, 256 ) ) > 0 ) 
	{
	    strncpy ( tmpData, strstr ( buf, "t=" ) + 2, 5 ); 
	    thetemp[i] = strtof ( tmpData, NULL );
	}
	close ( fd );
	char tempstr[320];
	snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", thetemp[i] / 1000.0 );
	retstr = retstr + tempstr + " ";
    }
    return ( retstr );
}

// reads i2c sht11 or si7021 sensors
std::string read_sht11 ( )
{
    std::string retstr = "";

    // create the I2C bus
    int file;
    const char *bus = "/dev/i2c-1";
    if ( ( file = open ( bus, O_RDWR ) ) < 0 ) 
    {
	//std::cout << "Fail! Could not open I2C-Bus!" << std::endl;
	return ( "X" );
    }

    // get i2c device, sht11 and si7021 i2c addresses are 0x40(64)
    ioctl ( file, I2C_SLAVE, 0x40 );

    // the command to send
    char config[1];

    // the data to read
    char data[2] = {0};

    // send humidity measurement command 0xF5
    config[0] = 0xF5;
    write ( file, config, 1 );
    sleep ( 1 );

    // read 2 bytes of humidity data: humidity msb, humidity lsb
    if ( read ( file, data, 2 ) != 2 )
    {
	//std::cout << "Fail! Error in reading SHT11 humidity!" << std::endl;
	return ( "X" );
    }
    else
    {
	// data conversion
	float humidity = ( ( ( data[0] * 256 + data[1] ) * 125.0 ) / 65536.0 ) - 6;
	char tempstr[320];
	snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", humidity );
	retstr = retstr + tempstr + " ";
    }

    // send temperature measurement command 0xF3
    config[0] = 0xF3;
    write ( file, config, 1 ); 
    sleep ( 1 );

    // read 2 bytes of temperature data: temperature msb, temperature lsb
    if ( read ( file, data, 2 ) != 2 )
    {
	//std::cout << "Fail! Error in reading SHT11 temperature!" << std::endl;
	return ( "X" );
    }
    else
    {
	// data conversion 
	float temperature = ( ( ( data[0] * 256 + data[1] ) * 175.72 ) / 65536.0 ) - 46.85;
	char tempstr[320];
	snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", temperature );
	retstr = retstr + tempstr + " ";
    }

    return ( retstr );
}

// the main program
int main ( int argc, char** argv )
{
    bool dht11on = false;
    bool w1on = false;
    bool sht11on = false;

    std::string filename = "";
    std::stringstream astream;

    /*
    char *mypath = NULL;
    char *dht11opts = NULL;
    int index;
    int c;
    opterr = 0;
    
    
    
    while ( ( c = getopt ( argc, argv, "abc:" ) ) != -1 )
    {
	switch ( c )
	{
	    case 'w1':
		w1on = true;
		std::cout << "W1 on!" << std::endl;
		break;
	    case 'dht11':
		dht11on = true;
		std::cout << "DHT11 on!" << std::endl;
		dht11opts = optarg;
		break;
	    case 'f':
		mypath = optarg;
		break;
	    case '?':
		if ( optopt == 'f' )
		{
		    fprintf (stderr, "Option -%c requires an argument.\n", optopt);
		}
		else if ( isprint ( optopt ) )
		{
		    fprintf (stderr, "Unknown option `-%c'.\n", optopt);
		}
		else
		{
		    fprintf (stderr,"Unknown option character `\\x%x'.\n",              optopt);
		}
		return 1;
	    default:
		abort ();
	}
    }

  for (index = optind; index < argc; index++)
    printf ("Non-option argument %s\n", argv[index]);
    
    */
    
    
    if ( argc>1 )
    {
	astream << argv[1];
	filename = astream.str ( );

	if ( argc>2 )
	{
	    for ( int i=2; i<argc; i++ )
	    {
		std::stringstream bstream;
		bstream << argv[i];
		if ( bstream.str ( ) == "dht11" )
		{
		    dht11on = true;
		    std::cout << "DHT11 is ON!" << std::endl;
		}
		if ( bstream.str ( ) == "w1" )
		{
		    w1on = true;
		    std::cout << "w1 is ON!" << std::endl;
		}
		if ( bstream.str ( ) == "sht11" )
		{
		    sht11on = true;
		    std::cout << "SHT11 is ON!" << std::endl;
		}
	    }
	}
	else
	{
	    std::cout << "No sensors specified, assuming all types..." << std::endl;
	    dht11on = true;
	    w1on = true;
	    sht11on = true;
	}

	std::cout << "Writing to file " << filename << "..." << std::endl;
	std::cout << "Hit control + c to quit!" << std::endl;
	filename = argv[1];
    }
    else
    {
	std::cout << "You did not enter a file name for output!" << std::endl;
	exit ( 1 );
    }

    std::ofstream myfile;
    myfile.open ( filename.c_str ( ), std::ios_base::app );
    if ( !myfile.is_open ( ) )
    {
	std::cout << "Error in opening output file!" << std::endl;
	exit ( 1 );
    }

    // check if wiringPi loaded - needed for dht11
    if ( wiringPiSetup ( ) == -1 && dht11on == true )
    {
	std::cout << "wiringPi not loaded! This is needed for DHT11 sensors!" << std::endl;
	exit ( 1 );
    }

    /*
    // gpio pin - 'gpio readall' prints a table of pins
    // set dht11 count
    int ndht11 = 0;
    int dhtadd[30] = { 0 };
    std::cout << "Probing DHT11s..." << std::endl;
    sleep ( 10 );
    for ( int i=0; i<30; i++ )
    {
	std::string tempstr = "";
	tempstr = read_dht11 ( i );
	if ( tempstr != "X" )
	{
	    std::cout << "Found DHT11 no. " << ndht11 << " at GPIO pin " << i << "!" << std::endl;
	    dhtadd[ ndht11 ] = i;
	    ndht11++;
	} else {
	    std::cout << "Didn't find sth at " << i << std::endl;
	}
	sleep ( 10 );
    }
    */
    
    int dhtadd[30] = { 0 };
    int ndht11 = 3;
    dhtadd[0] = 0;
    dhtadd[1] = 1;
    dhtadd[2] = 2;
    dhtadd[3] = 3;

    // get the w1 devices
    if ( w1on == true )
    {
	DIR *dir;
	struct dirent *dirent;
	std::vector<std::string> devices;
	dir = opendir ( path );
	if ( dir != NULL )
	{
	    while ( ( dirent = readdir ( dir ) ) )
	    // devices begin with 10-
	    if ( dirent->d_type == DT_LNK && strstr( dirent->d_name, "10-" ) != NULL )
	    { 
		strcpy ( dev[w1count], dirent->d_name );
		std::cout << "Found w1 device " << w1count << ": " << dev[w1count] << std::endl;
		w1count++;
		if ( w1count > 20 )
		{
		    std::cout << "Warning! Found more than 20 1-Wire sensors!" << std::endl;
		    exit ( 1 );
		}
	    }
	    ( void ) closedir ( dir );
	}
	else
	{
	    std::cout << "Couldn't open the device directory!" << std::endl;
	    exit ( 1 );
	}
    }

    // delay in s
    int delayrate = 1;

    while ( 1 )
    {
	std::string thetime = gettime ( );
	std::string mydht11 = "";
	std::string myw1 = "";
	std::string mysht11 = "";

	if ( dht11on == true )
	{
	    for ( int i = 0; i < ndht11; i++ )
	    {
		mydht11 += read_dht11 ( dhtadd[i] ) + " ";
	    }
	}

	if ( w1on == true )
	{
	    myw1 = read_w1 ( );
	}

	if ( sht11on == true )
	{
	    mysht11 = read_sht11 ( );
	}

	std::size_t found_dht11 = mydht11.find ( "X" );
	std::size_t found_w1 = myw1.find ( "X" );
	std::size_t found_sht11 = mysht11.find ( "X" );
	if ( found_dht11 != std::string::npos )
	{
	    delayrate++;
	    std::cout << "Failed to read a DHT11 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else if ( found_w1 != std::string::npos )
	{
	    delayrate++;
	    std::cout << "Failed to read a w1 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else if ( found_sht11 != std::string::npos )
	{
	    delayrate++;
	    std::cout << "Failed to read a SHT11 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else
	{
	    std::cout << thetime << " " << mydht11 << myw1 << mysht11 << std::endl;
	    myfile << thetime << " " << mydht11 << myw1 << mysht11 << "\n";
	    myfile.flush ( );
	    delayrate = 1;
	}

	sleep ( delayrate );
    }
    return ( 0 );
}
