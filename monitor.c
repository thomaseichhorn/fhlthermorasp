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
#define DHTPIN 7

// w1 ID - 10 is considered the max usable count
char dev[20][16];

// w1 path
char path[] = "/sys/bus/w1/devices";

// found devices
int w1count = 0;

// read a dht11
std::string read_dht11()
{
    int dht11_dat[5] = { 0 };
    uint8_t laststate = HIGH;
    uint8_t counter = 0;
    uint8_t j = 0;

    // pull pin down for at least 18 milliseconds
    pinMode( DHTPIN, OUTPUT );
    digitalWrite( DHTPIN, LOW );
    delay( 20 );

    // then pull it up for 40 microseconds
    digitalWrite( DHTPIN, HIGH );
    delayMicroseconds( 40 );

    // prepare to read the pin
    pinMode( DHTPIN, INPUT );

    // detect change and read data
    for ( int i = 0; i < MAXTIMINGS; i++ )
    {
	counter = 0;
	while ( digitalRead( DHTPIN ) == laststate )
	{
	    counter++;
	    delayMicroseconds( 1 );
	    if ( counter == 255 )
	    {
		break;
	    }
	}
	laststate = digitalRead( DHTPIN );

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
	snprintf( retstr, sizeof( retstr ), "%d.%d %% %d.%d *C", dht11_dat[0], dht11_dat[1], dht11_dat[2], dht11_dat[3] );
	return( retstr );
    } else  {
	//std::cout << " Fail! Output is " << dht11_dat[0] << " " << dht11_dat[1]<< " " << dht11_dat[2]<< " " << dht11_dat[3] << " !" << std::endl;
	return( "X" );
    }
}

// returns the current time in a formatted string
std::string gettime()
{
    time_t rawtime;
    struct tm * timeinfo;
    time ( &rawtime );
    timeinfo = localtime ( &rawtime );
    char timebuffer [90];
    strftime ( timebuffer, 80, "%Y-%m-%d %H:%M:%S", timeinfo );
    return( timebuffer );
}

// reads 1-Wire sensors
std::string read_w1()
{
    double thetemp[20] = { 0.0 };
    std::string retstr;
    for (int i=0; i<w1count; i++)
    {
	// Path to device
	char devPath[128];

	// Data from device
	char buf[256];

	// Temp C * 1000 reported by device 
	char tmpData[6];

	ssize_t numRead;
	sprintf( devPath, "%s/%s/w1_slave", path, dev[i] );
	int fd = open( devPath, O_RDONLY );
	if( fd == -1 )
	{
	    // read error
	    return( "X" );
	}
	while( ( numRead = read( fd, buf, 256 ) ) > 0 ) 
	{
	    strncpy( tmpData, strstr( buf, "t=" ) + 2, 5 ); 
	    thetemp[i] = strtof( tmpData, NULL );
	}
	close( fd );
	std::ostringstream ss;

	// 2 digit precision
	double f = pow( 10, 2 );
	ss << ( ( ( int ) ( thetemp[i] / 1000.0*f ) ) /f );
	retstr = retstr + ss.str() + " *C ";
    }
    return( retstr );
}

int main( int argc, char** argv )
{
    std::string filename = "";
    std::stringstream astream;
    if ( argc>1 )
    {
	astream << argv[1];
	filename = astream.str();
	std::cout << "Writing to file " << filename << "..." << std::endl;
	std::cout << "Hit control + c to quit!" << std::endl;
	filename = argv[1];
    } else {
	std::cout << "You did not enter a file name for output!" << std::endl;
        exit( 1 );
    }

    std::ofstream myfile (filename.c_str());
    if( !myfile.is_open() )
    {
	std::cout << "Error in opening output file!" << std::endl;
    }

    // check if wiringPi loaded - needed for dht11
    if ( wiringPiSetup() == -1 )
    {
	std::cout << "wiringPi not loaded!" << std::endl;
	exit( 1 );
    }

    // get the w1 devices
    DIR *dir;
    struct dirent *dirent;
    std::vector<std::string> devices;
    dir = opendir ( path );
    if ( dir != NULL )
    {
	while ( dirent = readdir (dir) )
	// devices begin with 10-
	if ( dirent->d_type == DT_LNK && strstr( dirent->d_name, "10-" ) != NULL )
	{ 
	    strcpy( dev[w1count], dirent->d_name );
	    //std::cout << "Found device " << w1count << ": " << dev[w1count] << std::endl;
	    w1count++;
	    if( w1count > 20 )
	    {
		std::cout << "Warning! Found more than 20 1-Wire sensors!" << std::endl;
		exit( 1 );
	    }
	}
	( void ) closedir ( dir );
    } else {
	    std::cout << "Couldn't open the device directory!" << std::endl;
	    exit( 1 );
    }

    // delay in s
    int delayrate = 1;

    while ( 1 )
    {
	std::string thetime = gettime();
	std::string mydht11 = read_dht11();
	std::string myw1 = read_w1();

	int dhtfail = 0;
	while ( mydht11 == "X" )
	{
	    mydht11 = read_dht11();
	    dhtfail++;
	    sleep( dhtfail );
	    if ( dhtfail > 10 )
	    {
		mydht11 = " ";
	    }
	}
	std::cout << thetime << " " << mydht11 << " " << myw1 << std::endl;
	myfile << thetime << " " << mydht11 << " " << myw1 << "\n";
	myfile.flush();

	sleep( delayrate );
    }
    return(0);
}
