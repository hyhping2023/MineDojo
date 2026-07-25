// --------------------------------------------------------------------------------------------------
//  Copyright (c) 2016 Microsoft Corporation
//  
//  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
//  associated documentation files (the "Software"), to deal in the Software without restriction,
//  including without limitation the rights to use, copy, modify, merge, publish, distribute,
//  sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//  
//  The above copyright notice and this permission notice shall be included in all copies or
//  substantial portions of the Software.
//  
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
//  NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
//  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
//  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// --------------------------------------------------------------------------------------------------

package com.microsoft.Malmo.MissionHandlers;

import io.netty.buffer.ByteBuf;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.ContainerMerchant;
import net.minecraftforge.fml.common.network.ByteBufUtils;
import net.minecraftforge.fml.common.network.simpleimpl.IMessage;
import net.minecraftforge.fml.common.network.simpleimpl.IMessageHandler;
import net.minecraftforge.fml.common.network.simpleimpl.MessageContext;

import com.microsoft.Malmo.MalmoMod;
import com.microsoft.Malmo.Schemas.MissionInit;

/**
 * Trade commands allow agents to interact with villagers.
 * Commands: "trade" to open trading GUI, "selectTrade <index>" to select a trade offer.
 */
public class TradeCommandsImplementation extends CommandBase
{
    private boolean isOverriding;

    public static class TradeMessage implements IMessage
    {
        String verb;
        String parameter;
        public TradeMessage()
        {
        }
    
        public TradeMessage(String verb, String parameter)
        {
            this.verb = verb;
            this.parameter = parameter;
        }

        @Override
        public void fromBytes(ByteBuf buf)
        {
            this.verb = ByteBufUtils.readUTF8String(buf);
            this.parameter = ByteBufUtils.readUTF8String(buf);
        }

        @Override
        public void toBytes(ByteBuf buf)
        {
            ByteBufUtils.writeUTF8String(buf, this.verb);
            ByteBufUtils.writeUTF8String(buf, this.parameter);
        }
    }

    public static class TradeMessageHandler implements IMessageHandler<TradeMessage, IMessage>
    {
        @Override
        public IMessage onMessage(final TradeMessage message, MessageContext ctx)
        {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null)
                return null;

            player.getServer().addScheduledTask(new Runnable()
            {
                @Override
                public void run()
                {
                    if (message.verb.equalsIgnoreCase("trade"))
                    {
                        // Enable GUI interact so the next right-click on a villager opens the trading GUI
                        MalmoMod.setAllowGuiInteract(true);
                    }
                    else if (message.verb.equalsIgnoreCase("selectTrade"))
                    {
                        if (player.openContainer instanceof ContainerMerchant)
                        {
                            ContainerMerchant container = (ContainerMerchant) player.openContainer;
                            try
                            {
                                int index = Integer.parseInt(message.parameter.trim());
                                if (index >= 0)
                                {
                                    container.setCurrentRecipeIndex(index);
                                    container.detectAndSendChanges();
                                }
                            }
                            catch (NumberFormatException e)
                            {
                                System.out.println("TradeCommands: invalid trade index: " + message.parameter);
                            }
                        }
                        else
                        {
                            System.out.println("TradeCommands: no trading GUI open");
                        }
                    }
                }
            });
            return null;
        }
    }

    @Override
    protected boolean onExecute(String verb, String parameter, MissionInit missionInit)
    {
        if (verb.equalsIgnoreCase("trade") || verb.equalsIgnoreCase("selectTrade"))
        {
            MalmoMod.network.sendToServer(new TradeMessage(verb, parameter));
            return true;
        }
        return false;
    }

    @Override
    public boolean parseParameters(Object params)
    {
        return true;
    }

    @Override
    public void install(MissionInit missionInit)
    {
    }

    @Override
    public void deinstall(MissionInit missionInit)
    {
    }

    @Override
    public boolean isOverriding()
    {
        return this.isOverriding;
    }

    @Override
    public void setOverriding(boolean b)
    {
        this.isOverriding = b;
    }
}
