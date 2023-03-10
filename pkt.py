from zlib import compress, decompress
import struct

GGWDSERVER_LANG = 0
GGWDSERVER_VERS = 16

ENDIANNESS = "little"
ENCODING = "utf-8"

# TODO Research the behavior when multiple commands are present


def unpack(packet):
    class Header:
        pass
    header = Header()
    header.packet_ordinal = int(struct.unpack("H", packet[:2])[0])
    header.client_language = int(struct.unpack("B", packet[2:3])[0])  # client language
    header.client_version = int(struct.unpack("B", packet[4:5])[0])  # client game
    data = decompress(packet[12:])
    functions = []
    fun_count = struct.unpack("B", data[0:1])[0]
    for function_n in range(0, fun_count):
        parameter_length = 0
        function_length = struct.unpack_from("B", data[2:3], False)[0]
        cursor = 5 + function_length
        functions.append([data[3:3 + function_length].decode(ENCODING), []])  # requested function
        param_n = struct.unpack("B", data[3 + function_length:4 + function_length])[0]  # quantity of parameters
        for _ in range(0, param_n):
            # buffer = data[cursor:cursor+2]
            parameter_length = struct.unpack("<H", data[cursor:cursor+2], )[0]
            cursor += 4
            value = data[cursor:cursor+parameter_length-1]
            functions[function_n][1].append(value)
            cursor += parameter_length
        data = data[cursor:]
    return header, functions


def pack(data, magicbytes):
    # first entry is action
    packet = bytearray()
    packet.extend(struct.pack("H", data.__len__()))  # number of functions in the packet
    fn = 0
    for function in data:
        data[fn].append(magicbytes)
        packet.extend(struct.pack("B", data[fn][0].__len__()))  # function length
        packet.extend(data[fn][0].encode(ENCODING))  # function name
        packet.extend(struct.pack("H", data[fn].__len__()-1))  # param count ?(don't count the function)
        for parameter in function[1:]:
            packet.extend(struct.pack("I", len(parameter)))
            # packet.extend([0x00, 0x00])
            packet.extend(parameter.encode(ENCODING))
        fn += 1
    return packet


def add_header(packet, request):
    datalen = len(packet)
    packeddata = compress(packet)
    finalizedpacket = bytearray()
    finalizedpacket.extend(request[:2])  # packet ordinal
    finalizedpacket.extend(struct.pack("B", GGWDSERVER_LANG))  # client language
    finalizedpacket.extend(struct.pack("B", GGWDSERVER_VERS))  # client game
    finalizedpacket.extend(struct.pack("I", len(packeddata) + 12))  # data + header size
    finalizedpacket.extend(struct.pack("I", datalen))  # unpacked data length
    finalizedpacket.extend(packeddata)
    return finalizedpacket


def handle_client(recvdata, recvaddr, keepalivesock, gamemanager):

    # datalen = len(recvdata)
    action_id = recvdata[4]

    if action_id == 22:
        publicaddr = bytearray()
        publicaddr.extend(recvdata[:4])
        publicaddr.extend(struct.pack('H', 17))
        octets = recvaddr[0].split(sep=".")

        for octet in octets:
            octetint = int(octet)
            octetint = struct.pack("B", octetint)
            publicaddr.extend(octetint)
        clientport = struct.pack("H", recvaddr[1])
        publicaddr.extend(clientport)
        keepalivesock.sendto(publicaddr, recvaddr)

    # Relays client network interfaces to the provided lobby host
    elif action_id == 24:
        hostaddr = recvdata[6:10]
        hostaddr = [str(byte) for byte in hostaddr]
        hostaddr = ".".join(hostaddr)

        for lobby in gamemanager.lobbies:

            if hostaddr == gamemanager.lobbies[lobby].host.ip_address[0]:
                recvdata = bytearray(recvdata)
                recvdata[-5:] = [0x25, 0xCD, 0x40, 0x6E, 0x3E]
                keepalivesock.sendto(recvdata, (hostaddr, 34000))

    else:
        pass
