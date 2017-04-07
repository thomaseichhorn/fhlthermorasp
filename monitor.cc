// compile with:
// g++ monitor.cc -o monitor -L/usr/local/lib -lwiringPi

#include <stdio.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <dirent.h>
#include <string.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <vector>
#include <string>
#include <time.h>
#include <wiringPi.h>
#include <stdint.h>
#include <sstream>
#include <cmath>

#define MAXTIMINGS 85

// w1 ID - 10 is considered the max usable count
char dev[20][16];

// w1 path
char path[] = "/sys/bus/w1/devices";

// found devices
int w1count = 0;

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
    //check we read 40 bits (8bit x 5 ) + verify checksum in the last byte
    if ( ( j >= 40 ) && ( dht11_dat[4] == ( ( dht11_dat[0] + dht11_dat[1] + dht11_dat[2] + dht11_dat[3] ) & 0xFF ) ) )
    {
	snprintf ( retstr, sizeof ( retstr ), "%d.%02d %d.%02d", dht11_dat[0], dht11_dat[1], dht11_dat[2], dht11_dat[3] );
	return ( retstr );
    } else  {
	//std::cout << " Fail! Output is " << dht11_dat[0] << " " << dht11_dat[1]<< " " << dht11_dat[2]<< " " << dht11_dat[3] << " !" << std::endl;
	return ( "X" );
    }
}

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

// reads 1-Wire sensors
std::string read_w1 ( )
{
    double thetemp[20] = { 0.0 };
    std::string retstr = "";
    for ( int i=0; i<w1count; i++ )
    {
	// Path to device
	char devPath[128];

	// Data from device
	char buf[256];

	// Temp C * 1000 reported by device 
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

int main ( int argc, char** argv )
{
    bool dht11on = false;
    bool w1on = false;

    std::string filename = "";
    std::stringstream astream;
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
	    }
	} else {
	    std::cout << "No sensors specified, assuming all types..." << std::endl;
	    dht11on = true;
	    w1on = true;
	}

	std::cout << "Writing to file " << filename << "..." << std::endl;
	std::cout << "Hit control + c to quit!" << std::endl;
	filename = argv[1];
    } else {
	std::cout << "You did not enter a file name for output!" << std::endl;
        exit ( 1 );
    }

    std::ofstream myfile;
    myfile.open ( filename.c_str ( ), std::ios_base::app );
    if ( !myfile.is_open( ) )
    {
	std::cout << "Error in opening output file!" << std::endl;
    }

    // check if wiringPi loaded - needed for dht11
    if ( wiringPiSetup ( ) == -1 )
    {
	std::cout << "wiringPi not loaded!" << std::endl;
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
    int ndht11 = 4;
    dhtadd[0] = 0;
    dhtadd[1] = 1;
    dhtadd[2] = 2;
    dhtadd[3] = 3;

    // get the w1 devices
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
	    strcpy( dev[w1count], dirent->d_name );
	    //std::cout << "Found device " << w1count << ": " << dev[w1count] << std::endl;
	    w1count++;
	    if ( w1count > 20 )
	    {
		std::cout << "Warning! Found more than 20 1-Wire sensors!" << std::endl;
		exit( 1 );
	    }
	}
	( void ) closedir ( dir );
    } else {
	    std::cout << "Couldn't open the device directory!" << std::endl;
	    exit ( 1 );
    }

    // delay in s
    int delayrate = 1;

    while ( 1 )
    {
	std::string thetime = gettime ( );
	std::string mydht11 = "";
	if ( dht11on == true )
	{
	    for ( int i = 0; i < ndht11; i++ )
	    {
		mydht11 += read_dht11 ( dhtadd[i] ) + " ";
	    }
	}

	std::string myw1 = "";

	if ( w1on == true )
	{
	    myw1 = read_w1 ( );
	}

	std::size_t found = mydht11.find ( "X" );
	if ( found != std::string::npos )
	{
	    //std::cout << "fail " << std::endl;
	    delayrate++;
	} else {
	    std::cout << thetime << " " << mydht11 << myw1 << std::endl;
	    myfile << thetime << " " << mydht11 << myw1 << "\n";
	    myfile.flush ( );
	    delayrate = 1;
	}

	sleep ( delayrate );
    }
    return ( 0 );
}
