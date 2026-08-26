-- DCS Lua Runner secure server.
-- Derived from DCS Fiddle by JonathanTurnock and john681611.
-- License: MIT (https://github.com/JonathanTurnock/dcsfiddle)

local SERVER_NAME = "DCS Lua Runner"
local PROTOCOL_VERSION = 1
local CONFIG_RELATIVE_PATH = "Scripts\\DCSLuaRunner\\dcs-fiddle-config.lua"
local HOOKS_RELATIVE_DIRECTORY = "Scripts\\Hooks\\"
local SERVER_FILENAME = "dcs-fiddle-server.lua"

local DEFAULT_LOG_LEVEL = 1 -- 0 = debug, 1 = info, 2 = errors only
local log_level = DEFAULT_LOG_LEVEL

local function write_log(level_name, message)
    local formatted = "[dcs-fiddle-server] - " .. tostring(message)
    if log and log[level_name] then
        log[level_name](formatted)
    elseif print then
        print(string.upper(level_name) .. " - " .. formatted)
    end
end

local function log_debug(message)
    if log_level <= 0 then
        write_log("debug", message)
    end
end

local function log_info(message)
    if log_level <= 1 then
        write_log("info", message)
    end
end

local function log_error(message)
    write_log("error", message)
end

if not require or not package then
    if env and env.error then
        env.error(
            "DCS Lua Runner requires the DCS Mission Scripting environment to expose require and package.",
            true
        )
    else
        log_error("Startup failed because require or package is unavailable")
    end
    return
end

package.path = package.path .. ";.\\LuaSocket\\?.lua"
package.cpath = package.cpath .. ";.\\LuaSocket\\?.dll"

local socket_ok, socket = pcall(require, "socket")
if not socket_ok or not socket then
    log_error("Startup failed because LuaSocket could not be loaded")
    return
end

local function resolve_saved_games_directory()
    local file_system = rawget(_G, "lfs")
    if not file_system then
        local loaded, module = pcall(require, "lfs")
        if loaded then
            file_system = module
        end
    end

    if not file_system or type(file_system.writedir) ~= "function" then
        return nil, "LuaFileSystem writedir() is unavailable"
    end

    local write_directory = file_system.writedir()
    if type(write_directory) ~= "string" or write_directory == "" then
        return nil, "LuaFileSystem writedir() returned an invalid path"
    end

    local final_character = write_directory:sub(-1)
    if final_character ~= "\\" and final_character ~= "/" then
        write_directory = write_directory .. "\\"
    end

    return write_directory
end

local function is_integer(value)
    return type(value) == "number" and value == math.floor(value)
end

local function require_integer(raw, name, minimum, maximum)
    local value = rawget(raw, name)
    if not is_integer(value) or value < minimum or value > maximum then
        error(string.format("%s must be an integer from %d through %d", name, minimum, maximum))
    end
    return value
end

local function require_number(raw, name, minimum, maximum)
    local value = rawget(raw, name)
    if type(value) ~= "number" or value < minimum or value > maximum then
        error(string.format("%s must be a number from %s through %s", name, minimum, maximum))
    end
    return value
end

local function validate_config(raw)
    if type(raw) ~= "table" or getmetatable(raw) ~= nil then
        error("configuration must return a plain Lua table")
    end

    local bind_ip = rawget(raw, "bind_ip")
    if bind_ip ~= "127.0.0.1" then
        error("bind_ip must be 127.0.0.1; remote interfaces are not permitted")
    end

    local proxy_token = rawget(raw, "proxy_token")
    if type(proxy_token) ~= "string" or #proxy_token < 43 or #proxy_token > 128 then
        error("proxy_token must contain 43 through 128 base64url characters")
    end
    if not proxy_token:match("^[A-Za-z0-9_-]+$") then
        error("proxy_token must use unpadded base64url characters")
    end
    if proxy_token:find("CHANGE", 1, true) or proxy_token:find("REPLACE", 1, true) then
        error("proxy_token still contains a placeholder value")
    end

    local config = {
        bind_ip = bind_ip,
        mission_port = require_integer(raw, "mission_port", 1, 65535),
        gui_port = require_integer(raw, "gui_port", 1, 65535),
        proxy_token = proxy_token,
        max_request_line_bytes = require_integer(raw, "max_request_line_bytes", 256, 8192),
        max_header_bytes = require_integer(raw, "max_header_bytes", 1024, 65536),
        max_body_bytes = require_integer(raw, "max_body_bytes", 1, 1048576),
        max_response_bytes = require_integer(raw, "max_response_bytes", 1024, 8388608),
        max_clients = require_integer(raw, "max_clients", 1, 64),
        max_json_depth = require_integer(raw, "max_json_depth", 1, 64),
        read_chunk_bytes = require_integer(raw, "read_chunk_bytes", 256, 65536),
        write_chunk_bytes = require_integer(raw, "write_chunk_bytes", 256, 65536),
        incomplete_request_deadline = require_number(raw, "incomplete_request_deadline", 0.5, 60),
        write_deadline = require_number(raw, "write_deadline", 0.5, 60),
        poll_interval = require_number(raw, "poll_interval", 0.01, 1),
        log_level = require_integer(raw, "log_level", 0, 2),
    }

    if config.mission_port == config.gui_port then
        error("mission_port and gui_port must be different")
    end

    return config
end

local function load_external_config()
    local injected = rawget(_G, "DCS_FIDDLE_CONFIG")
    _G.DCS_FIDDLE_CONFIG = nil
    if injected ~= nil then
        return validate_config(injected), nil
    end

    local saved_games_directory, directory_error = resolve_saved_games_directory()
    if not saved_games_directory then
        error(directory_error)
    end

    local config_path = saved_games_directory .. CONFIG_RELATIVE_PATH
    local config_chunk, load_error = loadfile(config_path)
    if not config_chunk then
        error("unable to load " .. CONFIG_RELATIVE_PATH .. ": " .. tostring(load_error))
    end

    local executed, raw_config = pcall(config_chunk)
    if not executed then
        error("unable to evaluate " .. CONFIG_RELATIVE_PATH .. ": " .. tostring(raw_config))
    end

    return validate_config(raw_config), saved_games_directory
end

local config_ok, config_or_error, saved_games_directory = pcall(load_external_config)
if not config_ok then
    log_error("Secure configuration rejected: " .. tostring(config_or_error))
    return
end

local config = config_or_error
log_level = config.log_level

local function is_valid_utf8(value)
    local index = 1
    local length = #value

    while index <= length do
        local first = value:byte(index)
        if first <= 0x7F then
            index = index + 1
        else
            local continuation_count
            local second_minimum = 0x80
            local second_maximum = 0xBF

            if first >= 0xC2 and first <= 0xDF then
                continuation_count = 1
            elseif first == 0xE0 then
                continuation_count = 2
                second_minimum = 0xA0
            elseif first >= 0xE1 and first <= 0xEC then
                continuation_count = 2
            elseif first == 0xED then
                continuation_count = 2
                second_maximum = 0x9F
            elseif first >= 0xEE and first <= 0xEF then
                continuation_count = 2
            elseif first == 0xF0 then
                continuation_count = 3
                second_minimum = 0x90
            elseif first >= 0xF1 and first <= 0xF3 then
                continuation_count = 3
            elseif first == 0xF4 then
                continuation_count = 3
                second_maximum = 0x8F
            else
                return false
            end

            if index + continuation_count > length then
                return false
            end
            local second = value:byte(index + 1)
            if second < second_minimum or second > second_maximum then
                return false
            end
            for offset = 2, continuation_count do
                local continuation = value:byte(index + offset)
                if continuation < 0x80 or continuation > 0xBF then
                    return false
                end
            end
            index = index + continuation_count + 1
        end
    end

    return true
end

local function json_escape(value)
    local escapes = {
        ["\\"] = "\\\\",
        ["\""] = "\\\"",
        ["\b"] = "\\b",
        ["\f"] = "\\f",
        ["\n"] = "\\n",
        ["\r"] = "\\r",
        ["\t"] = "\\t",
    }

    return '"' .. value:gsub('[%z\1-\31\\"]', function(character)
        return escapes[character] or string.format("\\u%04x", character:byte())
    end) .. '"'
end

local function encode_number(value)
    if value ~= value or value == math.huge or value == -math.huge then
        error("non-finite number at result value")
    end
    return string.format("%.14g", value)
end

local function table_shape(value)
    local count = 0
    local maximum = 0
    local array_candidate = true
    local string_keys_only = true
    local uses_reserved_envelope_key = false

    for key in pairs(value) do
        count = count + 1
        if type(key) == "number" and key >= 1 and key == math.floor(key) then
            if key > maximum then
                maximum = key
            end
        else
            array_candidate = false
        end
        if type(key) ~= "string" then
            string_keys_only = false
        elseif key == "__dcs_type" then
            uses_reserved_envelope_key = true
        end
    end

    if count == 0 then
        return "array", 0
    end
    if array_candidate and maximum == count then
        return "array", maximum
    end
    if string_keys_only and not uses_reserved_envelope_key then
        return "object", count
    end
    return "typed", count
end

local function compare_typed_entries(left, right)
    local ranks = { number = 1, string = 2, boolean = 3 }
    local left_type = type(left.key)
    local right_type = type(right.key)
    if left_type ~= right_type then
        return (ranks[left_type] or 99) < (ranks[right_type] or 99)
    end
    if left_type == "number" then
        return left.key < right.key
    end
    return tostring(left.key) < tostring(right.key)
end

local encode_json_value

local function encode_json_table(value, stack, path, depth)
    if stack[value] then
        error("circular reference at " .. path .. " (first seen at " .. stack[value] .. ")")
    end
    if depth > config.max_json_depth then
        error("maximum result depth exceeded at " .. path)
    end

    stack[value] = path
    local shape, length = table_shape(value)
    local encoded

    if shape == "array" then
        local items = {}
        for index = 1, length do
            items[index] = encode_json_value(value[index], stack, path .. "[" .. index .. "]", depth + 1)
        end
        encoded = "[" .. table.concat(items, ",") .. "]"
    elseif shape == "object" then
        local keys = {}
        for key in pairs(value) do
            table.insert(keys, key)
        end
        table.sort(keys)

        local fields = {}
        for _, key in ipairs(keys) do
            if not is_valid_utf8(key) then
                error("invalid UTF-8 table key at " .. path)
            end
            table.insert(
                fields,
                json_escape(key) .. ":" .. encode_json_value(value[key], stack, path .. "." .. key, depth + 1)
            )
        end
        encoded = "{" .. table.concat(fields, ",") .. "}"
    else
        local entries = {}
        for key, entry_value in pairs(value) do
            local key_type = type(key)
            if key_type ~= "number" and key_type ~= "string" and key_type ~= "boolean" then
                error("unsupported table key type " .. key_type .. " at " .. path)
            end
            if key_type == "number" then
                encode_number(key)
            end
            table.insert(entries, { key = key, value = entry_value })
        end
        table.sort(entries, compare_typed_entries)

        local encoded_entries = {}
        for _, entry in ipairs(entries) do
            local key_type = type(entry.key)
            local encoded_key
            if key_type == "string" then
                if not is_valid_utf8(entry.key) then
                    error("invalid UTF-8 table key at " .. path)
                end
                encoded_key = json_escape(entry.key)
            elseif key_type == "number" then
                encoded_key = encode_number(entry.key)
            else
                encoded_key = tostring(entry.key)
            end
            local entry_path = path .. "[" .. tostring(entry.key) .. "]"
            table.insert(
                encoded_entries,
                "{" ..
                    '"key_type":' .. json_escape(key_type) .. "," ..
                    '"key":' .. encoded_key .. "," ..
                    '"value":' .. encode_json_value(entry.value, stack, entry_path, depth + 1) ..
                "}"
            )
        end
        encoded = '{"__dcs_type":"table","entries":[' .. table.concat(encoded_entries, ",") .. "]}"
    end

    stack[value] = nil
    return encoded
end

encode_json_value = function(value, stack, path, depth)
    local value_type = type(value)
    if value_type == "nil" then
        return "null"
    elseif value_type == "string" then
        if not is_valid_utf8(value) then
            error("invalid UTF-8 string at " .. path)
        end
        return json_escape(value)
    elseif value_type == "number" then
        return encode_number(value)
    elseif value_type == "boolean" then
        return tostring(value)
    elseif value_type == "table" then
        return encode_json_table(value, stack, path, depth)
    end
    error("unsupported result type " .. value_type .. " at " .. path)
end

local function encode_json(value)
    local success, encoded_or_error = pcall(encode_json_value, value, {}, "$", 1)
    if not success then
        return nil, tostring(encoded_or_error)
    end
    return encoded_or_error
end

local function sanitize_message(message)
    local sanitized = tostring(message or "Request failed")
    sanitized = sanitized:gsub("[%z\1-\8\11\12\14-\31\127]", "?")
    sanitized = sanitized:gsub("[\r\n]+", " ")
    if not is_valid_utf8(sanitized) then
        sanitized = sanitized:gsub("[\128-\255]", "?")
    end
    if #sanitized > 1024 then
        sanitized = sanitized:sub(1, 1024) .. "..."
    end
    return sanitized
end

local function constant_time_equals(left, right)
    if type(left) ~= "string" or type(right) ~= "string" then
        return false
    end

    local maximum = math.max(#left, #right)
    local difference = math.abs(#left - #right)
    for index = 1, maximum do
        difference = difference + math.abs((left:byte(index) or 0) - (right:byte(index) or 0))
    end
    return difference == 0
end

local STATUS_TEXT = {
    [200] = "OK",
    [400] = "Bad Request",
    [401] = "Unauthorized",
    [404] = "Not Found",
    [405] = "Method Not Allowed",
    [408] = "Request Timeout",
    [411] = "Length Required",
    [413] = "Payload Too Large",
    [415] = "Unsupported Media Type",
    [422] = "Unprocessable Entity",
    [429] = "Too Many Requests",
    [431] = "Request Header Fields Too Large",
    [500] = "Internal Server Error",
    [503] = "Service Unavailable",
    [505] = "HTTP Version Not Supported",
}

local request_sequence = 0

local function next_request_id()
    request_sequence = (request_sequence % 999999999) + 1
    return string.format("dcs-%09d", request_sequence)
end

local function valid_request_id(value)
    return type(value) == "string" and #value >= 1 and #value <= 64 and value:match("^[%w._-]+$") ~= nil
end

local function error_body(request_id, kind, message)
    return "{" ..
        '"ok":false,' ..
        '"request_id":' .. json_escape(request_id) .. "," ..
        '"error":{' ..
            '"kind":' .. json_escape(kind) .. "," ..
            '"message":' .. json_escape(sanitize_message(message)) ..
        "}}"
end

local function build_response(status, body, request_id)
    local headers = {
        "Content-Type: application/json; charset=utf-8",
        "Content-Length: " .. tostring(#body),
        "Connection: close",
        "Cache-Control: no-store",
        "X-Request-ID: " .. request_id,
        "Server: " .. SERVER_NAME,
    }
    return "HTTP/1.1 " .. tostring(status) .. " " .. (STATUS_TEXT[status] or "Error") .. "\r\n" ..
        table.concat(headers, "\r\n") .. "\r\n\r\n" .. body
end

local function parse_target(target)
    if #target > config.max_request_line_bytes or target:sub(1, 1) ~= "/" or target:find("#", 1, true) then
        return nil, "invalid request target"
    end

    local path, query = target:match("^([^?]*)%??(.*)$")
    local parameters = {}
    if query and query ~= "" then
        for part in query:gmatch("[^&]+") do
            local name, value = part:match("^([^=]+)=(.*)$")
            if not name or parameters[name] ~= nil then
                return nil, "malformed or duplicate query parameter"
            end
            if name ~= "env" then
                return nil, "unsupported query parameter"
            end
            parameters[name] = value
        end
    end

    return { path = path, parameters = parameters }
end

local SINGLETON_HEADERS = {
    ["content-length"] = true,
    ["content-type"] = true,
    ["host"] = true,
    ["transfer-encoding"] = true,
    ["x-dcs-proxy-token"] = true,
    ["x-request-id"] = true,
}

local function parse_request_head(header_block)
    local lines = {}
    for line in (header_block .. "\r\n"):gmatch("(.-)\r\n") do
        table.insert(lines, line)
    end

    local request_line = table.remove(lines, 1)
    if not request_line or #request_line > config.max_request_line_bytes then
        return nil, 400, "bad_request", "request line is missing or too long", next_request_id()
    end

    local method, target, protocol = request_line:match("^(%S+) (%S+) (%S+)$")
    if not method or not target or not protocol then
        return nil, 400, "bad_request", "malformed request line", next_request_id()
    end
    if protocol ~= "HTTP/1.1" then
        return nil, 505, "bad_request", "only HTTP/1.1 is supported", next_request_id()
    end

    local headers = {}
    local counts = {}
    for _, line in ipairs(lines) do
        if line == "" or line:match("^[ \t]") then
            return nil, 400, "bad_request", "malformed request header", next_request_id()
        end
        local name, value = line:match("^([^:]+):[ \t]*(.*)$")
        if not name or not name:match("^[%w!#$%%&'*+%.%^_`|~-]+$") then
            return nil, 400, "bad_request", "malformed request header", next_request_id()
        end
        if value:find("[%z\1-\8\11\12\14-\31\127]") then
            return nil, 400, "bad_request", "invalid request header value", next_request_id()
        end

        name = name:lower()
        value = value:gsub("^[ \t]+", ""):gsub("[ \t]+$", "")
        counts[name] = (counts[name] or 0) + 1
        if SINGLETON_HEADERS[name] and counts[name] > 1 then
            return nil, 400, "bad_request", "duplicate security-sensitive header", next_request_id()
        end
        if headers[name] then
            headers[name] = headers[name] .. "," .. value
        else
            headers[name] = value
        end
    end

    local request_id = valid_request_id(headers["x-request-id"]) and headers["x-request-id"] or next_request_id()
    local parsed_target, target_error = parse_target(target)
    if not parsed_target then
        return nil, 400, "bad_request", target_error, request_id
    end
    if headers["transfer-encoding"] then
        return nil, 400, "bad_request", "transfer encoding is not supported", request_id
    end
    if not constant_time_equals(headers["x-dcs-proxy-token"], config.proxy_token) then
        return nil, 401, "authentication_failed", "proxy authentication failed", request_id
    end

    local request = {
        method = method,
        path = parsed_target.path,
        parameters = parsed_target.parameters,
        headers = headers,
        request_id = request_id,
        expected_length = 0,
    }

    if request.path == "/v1/execute" then
        if method ~= "POST" then
            return nil, 405, "unsupported_method", "execution requires POST", request_id
        end
        if request.parameters.env ~= "default" then
            return nil, 400, "unsupported_environment", "env must be default", request_id
        end
        if not headers["content-length"] then
            return nil, 411, "bad_request", "Content-Length is required", request_id
        end
        if not headers["content-length"]:match("^%d+$") then
            return nil, 400, "bad_request", "Content-Length must be a non-negative integer", request_id
        end
        request.expected_length = tonumber(headers["content-length"])
        if request.expected_length > config.max_body_bytes then
            return nil, 413, "payload_too_large", "Lua source exceeds the configured limit", request_id
        end

        local content_type = (headers["content-type"] or ""):lower():gsub("[ \t]", "")
        if content_type ~= "text/plain" and content_type ~= "text/plain;charset=utf-8" then
            return nil, 415, "bad_request", "Content-Type must be text/plain with UTF-8", request_id
        end
        request.action = "execute"
    elseif request.path == "/healthz" then
        if method ~= "GET" then
            return nil, 405, "unsupported_method", "health requires GET", request_id
        end
        if headers["content-length"] and headers["content-length"] ~= "0" then
            return nil, 400, "bad_request", "health requests cannot contain a body", request_id
        end
        request.action = "health"
    else
        return nil, 404, "bad_request", "route not found", request_id
    end

    return request
end

local function execute_lua(lua_source, request_id)
    if not is_valid_utf8(lua_source) then
        return nil, 400, "bad_request", "Lua source must be valid UTF-8"
    end

    local loaded, syntax_error = loadstring(lua_source, "dcs-fiddle-request")
    if not loaded then
        return nil, 422, "syntax_error", sanitize_message(syntax_error)
    end

    local executed, result = pcall(loaded)
    if not executed then
        return nil, 500, "runtime_error", sanitize_message(result)
    end

    local encoded_result, serialization_error = encode_json(result)
    if not encoded_result then
        return nil, 500, "serialization_error", sanitize_message(serialization_error)
    end

    local body = "{" ..
        '"ok":true,' ..
        '"request_id":' .. json_escape(request_id) .. "," ..
        '"result":' .. encoded_result ..
        "}"
    if #body > config.max_response_bytes then
        return nil, 500, "serialization_error", "encoded result exceeds the configured response limit"
    end
    return body, 200
end

local function health_body(request_id, environment_name)
    return "{" ..
        '"ok":true,' ..
        '"request_id":' .. json_escape(request_id) .. "," ..
        '"protocol_version":' .. tostring(PROTOCOL_VERSION) .. "," ..
        '"environment":' .. json_escape(environment_name) .. "," ..
        '"ready":true' ..
        "}"
end

local function create_http_server(address, port, environment_name)
    local tcp_server, bind_error = socket.bind(address, port)
    if not tcp_server then
        return nil, "could not bind " .. address .. ":" .. tostring(port) .. ": " .. tostring(bind_error)
    end
    tcp_server:settimeout(0)

    local clients = {}
    local client_sequence = 0

    local function close_client(client)
        if not client.closed then
            client.closed = true
            pcall(function()
                client.socket:close()
            end)
            clients[client.id] = nil
        end
    end

    local function queue_response(client, status, body, request_id)
        local safe_request_id = valid_request_id(request_id) and request_id or next_request_id()
        client.send_buffer = build_response(status, body, safe_request_id)
        client.send_index = 1
        client.state = "writing_response"
        client.deadline = socket.gettime() + config.write_deadline
    end

    local function queue_error(client, status, kind, message, request_id)
        local safe_request_id = valid_request_id(request_id) and request_id or next_request_id()
        log_info("Request rejected id=" .. safe_request_id .. " kind=" .. kind .. " status=" .. status)
        queue_response(client, status, error_body(safe_request_id, kind, message), safe_request_id)
    end

    local function process_received_bytes(client, bytes)
        if bytes and #bytes > 0 then
            client.receive_buffer = client.receive_buffer .. bytes
        end

        if client.state == "reading_headers" then
            local delimiter_start = client.receive_buffer:find("\r\n\r\n", 1, true)
            if not delimiter_start then
                if #client.receive_buffer > config.max_header_bytes then
                    queue_error(client, 431, "bad_request", "request headers exceed the configured limit")
                end
                return
            end

            local header_block = client.receive_buffer:sub(1, delimiter_start - 1)
            if #header_block > config.max_header_bytes then
                queue_error(client, 431, "bad_request", "request headers exceed the configured limit")
                return
            end

            local body_prefix = client.receive_buffer:sub(delimiter_start + 4)
            local request, status, kind, message, request_id = parse_request_head(header_block)
            if not request then
                queue_error(client, status, kind, message, request_id)
                return
            end

            client.request = request
            client.receive_buffer = body_prefix
            if #body_prefix > request.expected_length then
                queue_error(client, 400, "bad_request", "request contains unexpected trailing bytes", request.request_id)
                return
            end
            if #body_prefix == request.expected_length then
                client.state = "ready_to_execute"
            else
                client.state = "reading_body"
            end
        elseif client.state == "reading_body" then
            if #client.receive_buffer > client.request.expected_length then
                queue_error(
                    client,
                    400,
                    "bad_request",
                    "request contains unexpected trailing bytes",
                    client.request.request_id
                )
            elseif #client.receive_buffer == client.request.expected_length then
                client.state = "ready_to_execute"
            end
        end
    end

    local function receive_from_client(client)
        local received, receive_error, partial = client.socket:receive(config.read_chunk_bytes)
        local bytes = received or partial
        process_received_bytes(client, bytes)

        if client.state == "writing_response" or client.state == "ready_to_execute" then
            return
        end
        if receive_error == "closed" then
            queue_error(
                client,
                400,
                "bad_request",
                "connection closed before request completed",
                client.request and client.request.request_id
            )
        elseif receive_error and receive_error ~= "timeout" then
            close_client(client)
        end
    end

    local function execute_ready_request(client, execution_used)
        local request = client.request
        if request.action == "health" then
            queue_response(client, 200, health_body(request.request_id, environment_name), request.request_id)
            return execution_used
        end
        if execution_used then
            queue_error(client, 429, "server_busy", "another Lua request is executing", request.request_id)
            return execution_used
        end

        log_info("Executing authorized request id=" .. request.request_id .. " environment=" .. environment_name)
        local body, status, kind, message = execute_lua(client.receive_buffer, request.request_id)
        if not body then
            queue_error(client, status, kind, message, request.request_id)
        else
            queue_response(client, status, body, request.request_id)
        end
        return true
    end

    local function write_to_client(client)
        local final_index = math.min(#client.send_buffer, client.send_index + config.write_chunk_bytes - 1)
        local sent, send_error, partial_index = client.socket:send(
            client.send_buffer,
            client.send_index,
            final_index
        )
        local last_index = sent or partial_index
        if last_index then
            client.send_index = last_index + 1
        end
        if client.send_index > #client.send_buffer then
            close_client(client)
        elseif send_error and send_error ~= "timeout" then
            close_client(client)
        end
    end

    local function reject_excess_client(client_socket)
        client_socket:settimeout(0)
        local request_id = next_request_id()
        local body = error_body(request_id, "server_busy", "connection limit reached")
        pcall(function()
            client_socket:send(build_response(503, body, request_id))
        end)
        pcall(function()
            client_socket:close()
        end)
    end

    local function accept_clients()
        for _ = 1, config.max_clients do
            local client_socket, accept_error = tcp_server:accept()
            if not client_socket then
                if accept_error and accept_error ~= "timeout" then
                    log_error("Accept failed: " .. tostring(accept_error))
                end
                break
            end

            local active_count = 0
            for _ in pairs(clients) do
                active_count = active_count + 1
            end
            if active_count >= config.max_clients then
                reject_excess_client(client_socket)
            else
                client_socket:settimeout(0)
                pcall(function()
                    client_socket:setoption("tcp-nodelay", true)
                end)
                client_sequence = client_sequence + 1
                local now = socket.gettime()
                clients[client_sequence] = {
                    id = client_sequence,
                    socket = client_socket,
                    state = "reading_headers",
                    receive_buffer = "",
                    deadline = now + config.incomplete_request_deadline,
                    closed = false,
                }
                log_debug("Accepted client id=" .. client_sequence)
            end
        end
    end

    local function poll()
        accept_clients()

        local ordered_clients = {}
        for _, client in pairs(clients) do
            table.insert(ordered_clients, client)
        end
        table.sort(ordered_clients, function(left, right)
            return left.id < right.id
        end)

        local execution_used = false
        local now = socket.gettime()
        for _, client in ipairs(ordered_clients) do
            if not client.closed then
                if now > client.deadline then
                    if client.state == "writing_response" then
                        close_client(client)
                    else
                        queue_error(
                            client,
                            408,
                            "bad_request",
                            "request deadline exceeded",
                            client.request and client.request.request_id
                        )
                    end
                end

                if not client.closed and
                    (client.state == "reading_headers" or client.state == "reading_body") then
                    receive_from_client(client)
                end
                if not client.closed and client.state == "ready_to_execute" then
                    execution_used = execute_ready_request(client, execution_used)
                end
                if not client.closed and client.state == "writing_response" then
                    write_to_client(client)
                end
            end
        end
    end

    local function close_clients()
        local snapshot = {}
        for _, client in pairs(clients) do
            table.insert(snapshot, client)
        end
        for _, client in ipairs(snapshot) do
            close_client(client)
        end
    end

    local bound_ip, bound_port = tcp_server:getsockname()
    log_info("Secure HTTP server ready on " .. tostring(bound_ip) .. ":" .. tostring(bound_port))

    return {
        poll = poll,
        close_clients = close_clients,
    }
end

local is_mission = not DCS
local environment_name = is_mission and "mission" or "hooks"
local port = is_mission and config.mission_port or config.gui_port
local server, server_error = create_http_server(config.bind_ip, port, environment_name)
if not server then
    log_error("Startup failed: " .. tostring(server_error))
    return
end

if is_mission then
    local function scheduled_poll(_, model_time)
        local success, poll_error = pcall(server.poll)
        if not success then
            log_error("Mission server poll failed: " .. tostring(poll_error))
        end
        return model_time + config.poll_interval
    end

    timer.scheduleFunction(scheduled_poll, nil, timer.getTime() + config.poll_interval)
    log_info("Mission environment server initialized")
    if env and env.info then
        env.info("DCS Lua Runner secure server initialized", false)
    end
else
    saved_games_directory = saved_games_directory or resolve_saved_games_directory()
    if not saved_games_directory then
        log_error("DCS Saved Games directory could not be resolved for Mission bootstrap")
        return
    end

    local server_path = (
        saved_games_directory .. HOOKS_RELATIVE_DIRECTORY .. SERVER_FILENAME
    ):gsub("\\", "/")
    local config_path = (saved_games_directory .. CONFIG_RELATIVE_PATH):gsub("\\", "/")
    local next_poll_at = 0
    local callbacks = {}

    function callbacks.onSimulationStart()
        local server_command = string.format("dofile(%q)", server_path)
        local bootstrap = string.format([[
local config_chunk, config_error = loadfile(%q)
if not config_chunk then error(config_error) end
local mission_config = config_chunk()
if type(mission_config) ~= "table" then error("DCS Lua Runner configuration must return a table") end
DCS_FIDDLE_CONFIG = mission_config
a_do_script(%q)
]], config_path, server_command)

        local result, is_error = net.dostring_in("mission", bootstrap)
        if is_error then
            log_error("Mission bootstrap failed: " .. sanitize_message(result))
        else
            log_info("Mission bootstrap requested")
        end
    end

    function callbacks.onSimulationFrame()
        local now = socket.gettime()
        if now >= next_poll_at then
            next_poll_at = now + config.poll_interval
            local success, poll_error = pcall(server.poll)
            if not success then
                log_error("Hooks server poll failed: " .. tostring(poll_error))
            end
        end
    end

    function callbacks.onSimulationStop()
        server.close_clients()
    end

    DCS.setUserCallbacks(callbacks)
    log_info("Hooks environment server initialized")
end
