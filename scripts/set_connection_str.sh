if [[ $0 == $BASH_SOURCE ]]; then
    echo The script need to be sourced >&2
    exit 1
fi

db_connect_str=`az keyvault secret show -n a01taskstore-db-connect-str --vault-name a01secret --query value -otsv`

export A01_DATABASE_URI=$db_connect_str

