test='hiui-ui-core hiui-app-home hiui-app-clients hiui-app-layout hiui-app-login hiui-app-sdwan hiui-app-settings hiui-app-relayd hiui-app-upgrade hiui-app-wireless hiui-app-network'
version='git-2022.273.40156-b4fd187-1'

# https://github.com/zzzzzhy/hiui/releases/download/v1.0/
for var in $(echo ${test} | awk '{split($0,arr," ");for(i in arr) print arr[i]}'); do
    curl -o /custom/$var.ipk "https://github.com/zzzzzhy/hiui/releases/download/v1.0/"$var"_"$version"_all.ipk"
done

curl -o /custom/hiui-rpc-core.ipk "https://github.com/zzzzzhy/hiui/releases/download/v1.0/"$var"_"$version"_all.ipk"
