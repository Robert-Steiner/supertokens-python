coreInfo=`curl -s -X GET \
"https://api.supertokens.io/0/core/latest?password=$SUPERTOKENS_API_KEY&planType=FREE&mode=DEV&version=$1" \
-H 'api-version: 0'`
if [[ `echo $coreInfo | jq .tag` == "null" ]]
then
    echo "fetching latest X.Y.Z version for core, X.Y version: $1, planType: FREE gave response: $coreInfo"
    exit 1
fi
coreTag=$(echo $coreInfo | jq .tag | tr -d '"')
coreVersion=$(echo $coreInfo | jq .version | tr -d '"')

pluginInterfaceVersionXY=`curl -s -X GET \
"https://api.supertokens.io/0/core/dependency/plugin-interface/latest?password=$SUPERTOKENS_API_KEY&planType=FREE&mode=DEV&version=$1" \
-H 'api-version: 0'`
if [[ `echo $pluginInterfaceVersionXY | jq .pluginInterface` == "null" ]]
then
    echo "fetching latest X.Y version for plugin-interface, given core X.Y version: $1, planType: FREE gave response: $pluginInterfaceVersionXY"
    exit 1
fi
pluginInterfaceVersionXY=$(echo $pluginInterfaceVersionXY | jq .pluginInterface | tr -d '"')

pluginInterfaceInfo=`curl -s -X GET \
"https://api.supertokens.io/0/plugin-interface/latest?password=$SUPERTOKENS_API_KEY&planType=FREE&mode=DEV&version=$pluginInterfaceVersionXY" \
-H 'api-version: 0'`
if [[ `echo $pluginInterfaceInfo | jq .tag` == "null" ]]
then
    echo "fetching latest X.Y.Z version for plugin-interface, X.Y version: $pluginInterfaceVersionXY, planType: FREE gave response: $pluginInterfaceInfo"
    exit 1
fi
pluginInterfaceTag=$(echo $pluginInterfaceInfo | jq .tag | tr -d '"')
pluginInterfaceVersion=$(echo $pluginInterfaceInfo | jq .version | tr -d '"')

echo "Testing with FREE core: $coreVersion, plugin-interface: $pluginInterfaceVersion"

cd ../../
git clone git@github.com:supertokens/supertokens-root.git
cd supertokens-root
if [[ $2 == "2.0" ]] || [[ $2 == "2.1" ]] || [[ $2 == "2.2" ]]
then
    git checkout 36e5af1b9a4e3b07247d0cf333cf82a071a78681
fi
echo -e "core,$1\nplugin-interface,$pluginInterfaceVersionXY" > modules.txt
./loadModules --ssh
cd supertokens-core
git checkout $coreTag
cd ../supertokens-plugin-interface
git checkout $pluginInterfaceTag
cd ../
echo $SUPERTOKENS_API_KEY > apiPassword
./utils/setupTestEnvLocal
cd ../project/

export INSTALL_DIR=../supertokens-root
mkdir test-results
TEST_FILES=$(circleci tests glob "**/test_*.py")
echo "$TEST_FILES" | circleci tests run --command="xargs pytest -vv -o junit_family=legacy --junitxml=test-results/junit.xml" --verbose --split-by=timings
