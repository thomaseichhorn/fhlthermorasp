// compile with:
// g++ monitor.cc -o monitor -L/usr/local/lib -lwiringPi

#include <cmath>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <getopt.h>
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

// found w1 devices
int w1count = 0;

// write individual sensor output for mrtg
bool mrtgoutput = false;

// global sensor count
int globalcount = 1;

// file output
bool fileoutput = false;

// help message
static void show_usage ( std::string name )
{
    std::cerr << "Usage: " << name << " [-f, --file] <outputfile> [Option(s)]" << std::endl;
    std::cerr << "\t-f, --file\t\tThe output file to write to." << std::endl;
    std::cerr << "\t\t\t\tIf no file is selected, messages are sent to stdout." << std::endl;
    std::cerr << "Options:" << std::endl;
    std::cerr << "\t-h, --help\t\tShow this help message" << std::endl;
    std::cerr << "\t-d, --dht11\t\tUse a DHT11 t/h sensor" << std::endl;
    std::cerr << "\t-w, --w1\t\tUse w1 t sensor(s)" << std::endl;
    std::cerr << "\t-s, --sht11\t\tUse a SHT11 t/h sensor" << std::endl;
    std::cerr << "\t-b, --bme280\t\tUse a BME-280 t/h/p sensor" << std::endl;
    std::cerr << "If no sensors are selected, all variants are probed!" << std::endl;
}

// writes to mrtg files
void mrtg_write ( std::string inputstring )
{
    std::string filename;
    std::stringstream ss;
    ss << globalcount;
    std::string str = ss.str ( );
    filename = "/var/www/scripts/sensoroutput/" + str + ".txt";
    std::ofstream outfile ( filename.c_str ( ) );
    outfile << inputstring << std::endl;
    outfile.close ( );
    globalcount++;
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

// read a bme280
std::string read_bme ( )
{
    // return string
    std::string retstr = "";

    // i2c bus
    const char *bus = "/dev/i2c-1";

    // raw calibration data
    char data[24] = { 0 };

    // temperature calibration coeff.
    int T[3] = { 0 };

    // pressure calibration coeff.
    int P[9] = { 0 };

    // humidity calibration coeff.
    int H[6] = { 0 };

    // the device
    int device = 0;

    // the register
    char reg[1] = { 0 };

    if ( ( device = open ( bus, O_RDWR ) ) < 0 )
    {
	std::cout << " BME-280 : Could not open I2C-Bus!" << std::endl;
	globalcount++;
	return ( "X" );
    }

    // get I2C device
    ioctl ( device, I2C_SLAVE, 0x77 );

    // get status
    reg[0] = 0xF3;
    write ( device, reg, 1 );
    if ( read ( device, data, 1 ) != 1 )
    {
	std::cout << " BME-280 : Unable to read device status!" << std::endl;
	globalcount++;
	return ( "X" );
    }
    char * start = &data[0];
    int total = 0;
    while ( * start )
    {
	total *= 2;
	if (*start++ == '1') total += 1;
    }
    // std::cout << total << std::endl;

    // read 24 bytes of calibration data from address(0x88)
    reg[0] = 0x88;
    write ( device, reg, 1 );
    if ( read ( device, data, 24 ) != 24 )
    {
	std::cout << " BME-280 : Unable to read temperature and pressure calibration data!" << std::endl;
	globalcount++;
	return ( "X" );
    }

    // temp coefficents
    T[0] = data[1] * 256 + data[0];
    T[1] = data[3] * 256 + data[2];
    if ( T[1] > 32767 )
    {
	T[1] -= 65536;
    }
    T[2] = data[5] * 256 + data[4];
    if ( T[2] > 32767 )
    {
	T[2] -= 65536;
    }

    // pressure coefficents
    P[0] = data[7] * 256 + data[6];
    for ( int i = 0; i < 8; i++ )
    {
	P[i + 1] = data[2 * i + 9] * 256 + data[2 * i + 8];
	if ( P[i + 1] > 32767 )
	{
	    P[i + 1] -= 65536;
	}
    }

    // humidity coefficents, part 1
    reg[0] = 0xA1;
    write ( device, reg, 1 );
    if ( read ( device, data, 1 ) != 1 )
    {
	std::cout << " BME-280 : Unable to read humidity calibration data, part 1!" << std::endl;
	globalcount++;
	return ( "X" );
    }
    H[0] = data[0];

    // part 2
    reg[0] = 0xE1;
    write ( device, reg, 1);
    if ( read ( device, data, 7 ) != 7 )
    {
	std::cout << " BME-280 : Unable to read humidity calibration data, part 2!" << std::endl;
	globalcount++;
	return ( "X" );
    }
    H[1] = data[1] * 256 + data[0];
    if ( H[1] > 32767 )
    {
	H[1] -= 65536;
    }
    H[2] = data[2] & 0xFF;
    H[3] = ( data[3] * 16 + ( data[4] * 0xF ) );
    if ( H[3] > 32767 )
    {
	H[3] -= 65536;
    }
    H[4] = ( data[4] / 16 ) + ( data[5] * 16 );
    if ( H[4] > 32767 )
    {
	H[4] -= 65536;
    }
    H[5] = data[6];
    if ( H[5] > 32767 )
    {
	H[5] -= 65536;
    }

    char config[2] = {0};
    // select control humidity register 0xF2
    // humidity oversampliung rate = 1 ( 0x01 )
    config[0] = 0xF2;
    config[1] = 0x01;
    write ( device, config, 2 );

    // select control measurement register 0xF4
    // normal mode, temp and pressure oversampling rate = 1 ( 0x27 )
    config[0] = 0xF4;
    config[1] = 0x27;
    write ( device, config, 2 );

    // select config register 0xF5
    // stand-by time = 1000 ms = 0xA0
    config[0] = 0xF5;
    config[1] = 0xA0;
    write ( device, config, 2 );
    sleep ( 1 );

    // read 8 bytes of data from register 0xF7
    // pressure msb1, pressure msb, pressure lsb, temperature msb1, temperature msb, temperature lsb, humidity lsb, humidity msb
    reg[0] = 0xF7;
    write ( device, reg, 1 );
    if ( read ( device, data, 8 ) != 8 )
    {
	std::cout << " BME-280 : Unable to read measurement data!" << std::endl;
	globalcount++;
	return ( "X" );
    }

    // onvert pressure, temperature and humidity data to 19-bits
    long pres_read = ( ( long ) ( data[0] * 65536 + ( ( long ) ( data[1] * 256 ) + ( long ) ( data[2] & 0xF0 ) ) ) ) / 16;
    long temp_read = ( ( long ) ( data[3] * 65536 + ( ( long ) ( data[4] * 256 ) + ( long ) ( data[5] & 0xF0 ) ) ) ) / 16;
    long humi_read = ( long ) ( data[6] * 256 + data[7] );

    // temperature offset calculations
    double temp1 = ( ( ( double ) temp_read ) / 16384.0 - ( ( double ) T[0] ) / 1024.0 ) * ( ( double ) T[1]);
    double temp2 = ( ( ( ( double ) temp_read ) / 131072.0 - ( ( double ) T[0] ) / 8192.0 ) * ( ( ( double ) temp_read ) / 131072.0 - ( ( double ) T[0] ) / 8192.0 ) ) * ( ( double ) T[2] );
    double temp3 = temp1 + temp2;
    double temperature = temp3 / 5120.0;

    // pressure offset calculations
    double pres1 = ( temp3 / 2.0 ) - 64000.0;
    double pres2 = pres1 * pres1 * ( ( double ) P[5] ) / 32768.0;
    pres2 = pres2 + pres1 * ( ( double ) P[4] ) * 2.0;
    pres2 = ( pres2 / 4.0 ) + ( ( ( double ) P[3] ) * 65536.0 );
    pres1 = ( ( ( double ) P[2] ) * pres1 * pres1 / 524288.0 + ( ( double ) P[1] ) * pres1 ) / 524288.0;
    pres1 = ( 1.0 + pres1 / 32768.0 ) * ( ( double ) P[0] );
    double pres3 = 1048576.0 - ( double ) pres_read;
    // don't divide by 0
    double pressure = 0.0;
    if ( pres1 != 0.0 )
    {
	pres3 = ( pres3 - ( pres2 / 4096.0 ) ) * 6250.0 / pres1;
	pres1 = ( ( double ) P[8] ) * pres3 * pres3 / 2147483648.0;
	pres2 = pres3 * ( ( double ) P[7] ) / 32768.0;
	pressure = ( pres3 + ( pres1 + pres2 + ( ( double ) P[6] ) ) / 16.0 ) / 100.0;
    }

    // humidity offset calculations
    double humi1 = temp3 - 76800.0;
    humi1 = ( humi_read - ( H[3] * 64.0 + H[4] / 16384.0 * humi1 ) ) * (H[1] / 65536.0 * ( 1.0 + H[5] / 67108864.0 * humi1 * ( 1.0 + H[2] / 67108864.0 * humi1 ) ) );
    double humidity = humi1 * ( 1.0 -  H[0] * humi1 / 524288.0 );
    if ( humidity > 100.0 )
    {
	humidity = 100.0;
    }
    else if ( humidity < 0.0 )
    {
	humidity = 0.0;
    }

    // calculate pressure at sea level from barometric formula
    // double alt = 100.0;
    // double pressure_nn = pressure * pow ( 1 - ( -0.0065 * alt ) / ( temperature + 273.16 ), 5.255 );
    // std::cout << "BME-280: Pressure: " << pressure << " hPa, pressure at sea level: " << pressure_nn << " hPa, humidity: " << humidity << " %, temperature: " << temperature << " degrees" << std::endl;

    char tempstr[320];
    snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", pressure );
    retstr = retstr + tempstr + " ";
    snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", humidity );
    retstr = retstr + tempstr + " ";
    snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", temperature );
    retstr = retstr + tempstr;

    return ( retstr );
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
	mrtg_write( retstr );
	return ( retstr );
    }
    else
    {
	std::cout << " DHT11(" << DHTPIN << "): Read error! Output is " << dht11_dat[0] << " " << dht11_dat[1]<< " " << dht11_dat[2]<< " " << dht11_dat[3] << " !" << std::endl;
	globalcount++;
	return ( "X" );
    }
}

// reads 1-Wire sensors
std::string read_w1 ( )
{
    double thetemp[20] = { 0.0 };
    std::string retstr = "";
    for ( int i = 0; i < w1count; i++ )
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
	    globalcount++;
	    std::cout << " w1(" << i << ")   : Read error!" << std::endl;
	    return ( "X" );
	}
	while ( ( numRead = read ( fd, buf, 256 ) ) > 0 ) 
	{
	    strncpy ( tmpData, strstr ( buf, "t=" ) + 2, 6 );
	    thetemp[i] = strtof ( tmpData, NULL );
	}
	close ( fd );
	char tempstr[320];
	snprintf ( tempstr, sizeof ( tempstr ), "%4.2f", thetemp[i] / 1000.0 );
	mrtg_write( tempstr );
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
	std::cout << " SHT11   : Read error! Could not open I2C-Bus!" << std::endl;
	globalcount++;
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
	std::cout << " SHT11   : Error in reading SHT11 humidity!" << std::endl;
	globalcount++;
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
	std::cout << " SHT11   : Error in reading SHT11 temperature!" << std::endl;
	globalcount++;
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

    mrtg_write( retstr );
    return ( retstr );
}

// the main program
int main ( int argc, char** argv )
{
    bool dht11on = false;
    bool w1on = false;
    bool sht11on = false;
    bool bmeon = false;

    std::string filename = "";

    if ( argc > 1 )
    {
	for ( int i = 1; i < argc; i++ )
	{
	    std::stringstream astream;
	    astream << argv[i];
	    if ( astream.str ( ) == "-h" || astream.str ( ) == "--help" )
	    {
		show_usage ( argv[0] );
		exit ( 0 );
	    }
	    else if ( astream.str ( ) == "-d" || astream.str ( ) == "--dht11" )
	    {
		dht11on = true;
		std::cout << "DHT11 is ON!" << std::endl;
	    }
	    else if ( astream.str ( ) == "-w" || astream.str ( ) == "--w1" )
	    {
		w1on = true;
		std::cout << "w1 is ON!" << std::endl;
	    }
	    else if ( astream.str ( ) == "-s" || astream.str ( ) == "--sht11" )
	    {
		sht11on = true;
		std::cout << "SHT11 is ON!" << std::endl;
	    }
	    else if ( astream.str ( ) == "-b" || astream.str ( ) == "--bme280" )
	    {
		bmeon = true;
		std::cout << "BME280 is ON!" << std::endl;
	    }
	    else if ( astream.str ( ) == "-f" || astream.str ( ) == "--file" )
	    {
		if ( ( i + 1 ) < argc )
		{
		    astream.str ( std::string ( ) );
		    astream << argv[i + 1];
		    fileoutput = true;
		    filename = astream.str ( );
		    std::cout << "Writing to file " << filename << "..." << std::endl;
		}
		else
		{
		    std::cerr << "Flag \"-f | --file\" invoked, but no file name specified!" << std::endl;
		    std::cerr << std::endl;
		    show_usage ( argv[0] );
		    exit ( -1 );
		}
		i++;
	    }
	    else
	    {
		std::cerr << "Unknown option \"" << astream.str ( ) << "\"" << std::endl;
		show_usage ( argv[0] );
		exit ( -1 );
	    }

	}

	// catch no sensors selected
	if ( !dht11on && !w1on && !sht11on && !bmeon)
	{
	    std::cout << "No sensors selected, probing all!" << std::endl;
	    dht11on = true;
	    w1on = true;
	    sht11on = true;
	    bmeon = true;
	}

	std::cout << "Hit control + c to quit!" << std::endl;
	std::cout << std::endl;
    }
    else
    {
	std::cout << "No arguments given, writing to stdout!" << std::endl;
	std::cout << "No sensors specified, assuming all types..." << std::endl;
	std::cout << "Run " << argv[0] << " --help  to show help!" << std::endl;
	std::cout << std::endl;
	dht11on = true;
	w1on = true;
	sht11on = true;
	bmeon = true;
	fileoutput = false;
    }

    std::ofstream myfile;
    if ( fileoutput == true )
    {
	myfile.open ( filename.c_str ( ), std::ios_base::app );
	if ( !myfile.is_open ( ) )
	{
	    std::cout << "Error in opening output file!" << std::endl;
	    exit ( 1 );
	}
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
    int ndht11 = 1;
    dhtadd[0] = 7;
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
    int delayrate = 2;

    while ( 1 )
    {
	std::string thetime = gettime ( );
	std::string mydht11 = "";
	std::string myw1 = "";
	std::string mysht11 = "";
	std::string mybme = "";

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

	if ( bmeon == true )
	{
	    mybme = read_bme ( );
	}

	std::size_t found_dht11 = mydht11.find ( "X" );
	std::size_t found_w1 = myw1.find ( "X" );
	std::size_t found_sht11 = mysht11.find ( "X" );
	std::size_t found_bme = mybme.find ( "X" );
	if ( found_dht11 != std::string::npos )
	{
	    if ( delayrate < 5 )
	    {
		delayrate++;
	    }
	    std::cout << " Failed to read a DHT11 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else if ( found_w1 != std::string::npos )
	{
	    if ( delayrate < 5 )
	    {
		delayrate++;
	    }
	    std::cout << " Failed to read a w1 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else if ( found_sht11 != std::string::npos )
	{
	    if ( delayrate < 5 )
	    {
		delayrate++;
	    }
	    std::cout << " Failed to read a SHT11 device, retrying in " << delayrate << " s..." << std::endl;
	}
	else if ( found_bme != std::string::npos )
	{
	    if ( delayrate < 5 )
	    {
		delayrate++;
	    }
	    std::cout << " Failed to read a BME device, retrying in " << delayrate << " s..." << std::endl;
	}
	else
	{
	    std::cout << thetime << " " << mydht11 << myw1 << mysht11 << mybme << std::endl;
	    if ( fileoutput == true )
	    {
		myfile << thetime << " " << mydht11 << myw1 << mysht11 << mybme << "\n";
		myfile.flush ( );
	    }
	    delayrate = 1;
	}

	sleep ( delayrate );

	// reset
	globalcount = 1;
    }
    return ( 0 );
}
